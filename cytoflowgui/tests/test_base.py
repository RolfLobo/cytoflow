#!/usr/bin/env python3.8
# coding: latin-1

# (c) Massachusetts Institute of Technology 2015-2018
# (c) Brian Teague 2018-2022
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
Created on Jan 4, 2018

@author: brian
'''

# select the 'null' pyface toolkit. an exception is raised if the qt toolkit
# is subsequently imported, but that's better than trying to actually create
# a Qt app if PyQt is accidentally imported.

from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'null'

# even so, sometimes events get dispatched to the UI handler.  
# make sure they go into a black hole
from traits.trait_notifiers import set_ui_handler
set_ui_handler(lambda *x, **y: None)

# use the sphinx autodoc module-mocker to mock out traitsui.qt
# because when it's imported, it starts a Qt Application

from cytoflowgui.tests.sphinx_mock import MockFinder
import sys; sys.meta_path.insert(0, MockFinder(['traitsui.qt']))  

# make sure that even if we're running locally, we're using the Agg output
import matplotlib
matplotlib.use("Agg")

from traits.api import HasTraits, TraitListObject, TraitDictObject

import unittest, multiprocessing, os, logging
from logging.handlers import QueueHandler, QueueListener

from cytoflowgui.workflow import LocalWorkflow, RemoteWorkflow
from cytoflowgui.workflow.workflow_item import WorkflowItem
from cytoflowgui.workflow.operations import ImportWorkflowOp, ChannelStatisticWorkflowOp, ThresholdWorkflowOp, ThresholdSelectionView
from cytoflowgui.workflow.subset import CategorySubset, RangeSubset
from cytoflowgui.utility import CallbackHandler

def remote_main(parent_workflow_conn, log_q, running_event):
    # this should only ever be main method after a spawn() call 
    # (not fork). So we should have a fresh logger to set up.
        
    # messages that end up at the root logger go to log_q
    h = QueueHandler(log_q) 
    logging.getLogger().handlers.clear()
    logging.getLogger().addHandler(h)
    
    # make sure that ALL messages get queued in the remote 
    # process -- we'll filter/handle then in the local
    # process
    logging.getLogger().setLevel(logging.DEBUG)   

    running_event.set()
    
    # some of the sklearn things get sad when there are lots of threads. 
    # this is not an issue under normal conditions, but when testing, 
    # reducing the number of allowed threads to 1 eliminates these
    # random crashes.
    
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits = 1):
        RemoteWorkflow().run(parent_workflow_conn)

class WorkflowTest(unittest.TestCase):
    
    def setUp(self):
        
        self.addTypeEqualityFunc(HasTraits, 'assertHasTraitsEqual')
        self.addTypeEqualityFunc(WorkflowItem, 'assertHasTraitsEqual')
        self.addTypeEqualityFunc(TraitListObject, 'assertTraitListEqual')
        self.addTypeEqualityFunc(TraitDictObject, 'assertTraitDictEqual')
                
        # communications channels
        parent_workflow_conn, child_workflow_conn = multiprocessing.Pipe()  
        running_event = multiprocessing.Event()
        
        # logging
        log_q = multiprocessing.Queue()
        
        def handle(record):
            logger = logging.getLogger(record.name)
            if logger.isEnabledFor(record.levelno):
                logger.handle(record)
                
        handler = CallbackHandler(handle)
        self.queue_listener = QueueListener(log_q, handler)
        self.queue_listener.start()

        remote_process = multiprocessing.Process(target = remote_main,
                                                 name = "remote process",
                                                 args = [parent_workflow_conn,
                                                         log_q,
                                                         running_event])
        
        remote_process.daemon = True
        remote_process.start() 
        running_event.wait()
        
        self.workflow = LocalWorkflow(child_workflow_conn)
        self.remote_process = remote_process

    def tearDown(self):
        self.workflow.shutdown_remote_process(self.remote_process)
        self.queue_listener.stop()
        
    def assertHasTraitsEqual(self, t1, t2, msg=None):
        metadata = {'transient' : lambda t: t is not True,
                    'status' : lambda t: t is not True}
        
        d1 = t1.trait_get(t1.copyable_trait_names(**metadata))
        d2 = t2.trait_get(t1.copyable_trait_names(**metadata))
        self.assertEqual(set(d1.keys()), set(d2.keys()))
        for k in d1.keys():
            self.assertEqual(d1[k], d2[k])
            
    def assertTraitListEqual(self, t1, t2, msg=None):
        self.assertEqual(len(t1), len(t2))
        
        for o1, o2 in zip(t1, t2):
            self.assertEqual(o1, o2)
    
    def assertTraitDictEqual(self, t1, t2, msg=None):
        self.assertEqual(set(t1.keys()), set(t2.keys()))
        
        for k in t1.keys():
            self.assertEqual(t1[k], t2[k])

        
class ImportedDataTest(WorkflowTest):
    
    def setUp(self):
        super().setUp()
        
        self.addTypeEqualityFunc(ImportWorkflowOp, 'assertHasTraitsEqual')
        self.addTypeEqualityFunc(ChannelStatisticWorkflowOp, 'assertHasTraitsEqual')
        
        import_op = ImportWorkflowOp()

        from cytoflow import Tube
        
        import_op.conditions = {"Dox" : "float", "IP" : "float", "Well" : "category"}
     
        self.cwd = os.path.dirname(os.path.abspath(__file__))
     
        tube1 = Tube(file = self.cwd + "/../../cytoflow/tests/data/Plate01/CFP_Well_A4.fcs",
                     conditions = {"Dox" : 1.0, "IP" : 1.0, "Well" : 'A'})
     
        tube2 = Tube(file = self.cwd + "/../../cytoflow/tests/data/Plate01/RFP_Well_A3.fcs",
                     conditions = {"Dox" : 1.0, "IP" : 10.0, "Well" : 'B'})

        tube3 = Tube(file = self.cwd + "/../../cytoflow/tests/data/Plate01/YFP_Well_A7.fcs",
                     conditions = {"Dox" : 10.0, "IP" : 1.0, "Well" : 'A'})
         
        tube4 = Tube(file = self.cwd + "/../../cytoflow/tests/data/Plate01/CFP_Well_B4.fcs",
                     conditions = {"Dox" : 10.0, "IP" : 10.0, "Well" : 'B'})
     
        tube5 = Tube(file = self.cwd + "/../../cytoflow/tests/data/Plate01/RFP_Well_A6.fcs",
                     conditions = {"Dox" : 100.0, "IP" : 1.0, "Well" : 'A'})

        tube6 = Tube(file = self.cwd + "/../../cytoflow/tests/data/Plate01/YFP_Well_C7.fcs",
                     conditions = {"Dox" : 100.0, "IP" : 100.0, "Well" : 'B'})

                     
        import_op.tubes = [tube1, tube2, tube3, tube4, tube5, tube6]
        
        wi = WorkflowItem(operation = import_op,
                          status = "waiting",
                          view_error = "Not yet plotted") 
        self.workflow.workflow.append(wi)
        
        import_op.do_estimate = True
        self.workflow.wi_waitfor(wi, 'status', 'valid')
        self.assertTrue(self.workflow.remote_eval("self.workflow[0].result is not None"))

        stats_op_1 = ChannelStatisticWorkflowOp()
        stats_op_1.name = "MeanByDoxIP"
        stats_op_1.channel = "Y2-A"
        stats_op_1.function_name = "Mean"
        stats_op_1.by = ['Dox', 'IP']
        stats_op_1.subset_list.append(CategorySubset(name = "Well",
                                                     values = ['A', 'B']))
        stats_op_1.subset_list.append(RangeSubset(name = "Dox",
                                                  values = [1.0, 10.0, 100.0]))
        stats_op_1.subset_list.append(RangeSubset(name = "IP",
                                                  values = [1.0, 10.0]))

        stats_wi_1 = WorkflowItem(operation = stats_op_1,
                                  status = "waiting",
                                  view_error = "Not yet plotted")
        self.workflow.workflow.append(stats_wi_1)
        self.workflow.wi_waitfor(stats_wi_1, 'status', 'valid')
        
        stats_op_2 = ChannelStatisticWorkflowOp()
        stats_op_2.name = "GeoMeanByDoxIP"
        stats_op_2.channel = "Y2-A"
        stats_op_2.function_name = "Geo.Mean */ SD"
        stats_op_2.by = ['Dox', 'IP']
        stats_op_2.subset_list.append(CategorySubset(name = "Well",
                                                     values = ['A', 'B']))
        stats_op_2.subset_list.append(RangeSubset(name = "Dox",
                                                  values = [1.0, 10.0, 100.0]))
        stats_op_2.subset_list.append(RangeSubset(name = "IP",
                                                  values = [1.0, 10.0]))
        
        stats_wi_2 = WorkflowItem(operation = stats_op_2,
                                  status = "waiting",
                                  view_error = "Not yet plotted")
        self.workflow.workflow.append(stats_wi_2)
        self.workflow.selected = stats_wi_2
        self.workflow.wi_waitfor(stats_wi_2, 'status', 'valid')

class TasbeTest(WorkflowTest):
    
    def setUp(self):
        super().setUp()
        
        self.addTypeEqualityFunc(ThresholdWorkflowOp, 'assertHasTraitsEqual')
        self.addTypeEqualityFunc(ThresholdSelectionView, 'assertHasTraitsEqual')
        
        op = ImportWorkflowOp()

        from cytoflow import Tube
             
        self.cwd = os.path.dirname(os.path.abspath(__file__))
     
        tube = Tube(file = self.cwd + "/../../cytoflow/tests/data/tasbe/rby.fcs")
        op.tubes = [tube]
        
        wi = WorkflowItem(operation = op,
                          status = "waiting",
                          view_error = "Not yet plotted") 
        self.workflow.workflow.append(wi)
        
        op.do_estimate = True
        self.workflow.wi_waitfor(wi, 'status', 'valid')
        self.assertTrue(self.workflow.remote_eval("self.workflow[0].result is not None"))
        
        op = ThresholdWorkflowOp()
                
        op.name = "Morpho"
        op.channel = "FSC-A"
        op.threshold = 100000

        wi = WorkflowItem(operation = op,
                          status = 'waiting')
        self.workflow.workflow.append(wi)     
        self.workflow.selected = wi 
        self.workflow.wi_waitfor(wi, 'status', 'valid')


# the following classes are more "mix-ins" than base classes -- that's why they
# don't inherit from unittest.TestCase
class BaseViewTest:
    
    def setUpView(self):
        pass
    
    # xfacet
    def testXfacet(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.huefacet = ""
        self.view.xfacet = "IP"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
         
    # yfacet
    def testYfacet(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.huefacet = ""
        self.view.yfacet = "IP"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # huefacet
    def testHueFacet(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.huefacet = "IP"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    # huescale
    def testHueScale(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.huefacet = "IP"
        self.view.huescale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    def testPlotParams(self):
        
        # title
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.title = "Title"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        # xlabel
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.xlabel = "X label"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        # ylabel
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.ylabel = "Y label"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        # huelabel
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.huelabel = "Hue label"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        # colwrap
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = "IP"
        self.view.plot_params.col_wrap = 2
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
           
        # sns_style
        for style in ['darkgrid', 'whitegrid', 'white', 'dark', 'ticks']:
            self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
            self.view.plot_params.sns_style = style
            self.workflow.wi_waitfor(self.wi, 'view_error', '')
             
        # sns_context
        for context in ['poster', 'talk', 'poster', 'notebook', 'paper']:
            self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
            self.view.plot_params.sns_context = context
            self.workflow.wi_waitfor(self.wi, 'view_error', '')
         
        # legend
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.legend = False
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        # sharex
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.sharex = False
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
 
        # sharey
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.sharey = False
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
 
        # despine
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.despine = False
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
 
    
class BaseDataViewTest(BaseViewTest):
    
    def setUpView(self):
        super().setUpView()
        
        self.view.subset_list.append(CategorySubset(name = "Well",
                                                    values = ['A', 'B']))
        self.view.subset_list.append(RangeSubset(name = "Dox",
                                                 values = [1.0, 10.0, 100.0]))

    # this is here, instead of in BaseViewTest, because
    # "Dox" is used as the variable in statistics tests
    def testXandYfacet(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.huefacet = ""
        self.view.xfacet = "Dox"
        self.view.yfacet = "Well"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # subset 
    def testSubset(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.subset_list[0].selected = ['A']
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    

    def testPlotParams(self):
        super().testPlotParams()
        
        # min_quantile
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.min_quantile = 0.01
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        # max_quantile
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.max_quantile = 0.90
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        
class Base1DViewTest(BaseDataViewTest):
    
    def setUpView(self):
        super().setUpView()
        
        # set the channel
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.channel = "Y2-A"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')    
        
    # change channel
    def testChannel(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.channel = "V2-A"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # scale (log)
    def testLogScale(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.scale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    
    # scale (logicle)
    def testLogicleScale(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.scale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        
    def testAll(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.scale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')

        self.view.scale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = "Dox"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = "Well"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = "Well"
        self.view.yfacet = "Dox"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = "Well"
        self.view.yfacet = "Dox"
        self.view.plotfacet = "IP"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = ""
        self.view.huefacet = "Dox"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.huefacet = "Dox"
        self.view.huescale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
     
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = ""
        self.view.yfacet = ""
        self.view.subset_list[0].selected = ['A']
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    def testPlotParams(self):
        super().testPlotParams()
 
        # limits       
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.lim = (0, 1000)
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        # orientation
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.orientation = "horizontal"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
 
        
class Base2DViewTest(BaseDataViewTest):
    
    def setUpView(self):
        super().setUpView()
        
        # set X, Y channels
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xchannel = "FSC-A"
        self.view.ychannel = "Y2-A"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    # xchannel    
    def testXchannel(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xchannel = "B1-A"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
    # xscale
    def testXScaleLog(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xscale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    def testXScaleLogicle(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xscale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # ychannel
    def testYchannel(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xchannel = "V2-A"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # yscale
    def testYScaleLog(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yscale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
    def testYScaleLogicle(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yscale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
    def testAll(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xscale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yscale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = "Dox"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = "Well"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = "Well"
        self.view.yfacet = "Dox"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = ""
        self.view.huefacet = "Dox"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.huefacet = "Dox"
        self.view.huescale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xfacet = ""
        self.view.yfacet = ""
        self.view.subset_list[0].selected = ['A']
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    def testPlotParams(self):
        super().testPlotParams()
        
        # xlim
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.xlim = (0, 1000)
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        # ylim
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.ylim = (0, 1000)
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        
class BaseStatisticsViewTest(BaseViewTest): 
    
    def setUpView(self):
        super().setUpView()
        self.view.variable = "Dox"
        self.view.current_plot = 10.0
    
    # variable
    def testVariable(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.variable = "IP"
        self.view.current_plot = 10.0
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # subset
    def testSubset(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')

        self.view.subset_list.append(RangeSubset(name = "Dox",
                                                 values = [1.0, 10.0, 100.0]))
        self.view.subset_list[0].low = 10.0
        self.view.subset_list[0].high = 100.0

        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
    
class Base1DStatisticsViewTest(BaseStatisticsViewTest):
    
    def setUpView(self):
        super().setUpView()
        self.view.statistic = "GeoMeanByDoxIP"
        self.view.feature = "Geo.Mean"
        
    # error_statistic
    def testErrorStatistic(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.error_low = "/SD"
        self.view.error_high = "*SD"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # scale
    def testScaleLog(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.statistic = "GeoMeanByDoxIP"
        self.view.feature = "Geo.Mean"
        self.view.scale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')        

    def testScaleLogicle(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.statistic = "GeoMeanByDoxIP"
        self.view.feature = "Geo.Mean"
        self.view.scale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')  
    
    def testPlotParams(self):
        super().testPlotParams()
        
        # orientation
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.orientation = "horizontal"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
 
        # limits
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.lim = (0,100)
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
 
        
class Base2DStatisticsViewTest(BaseStatisticsViewTest):
    
    def setUpView(self):
        
        super().setUpView()
        self.view.statistic = "GeoMeanByDoxIP"
        self.view.xfeature = "Geo.Mean"
        self.view.yfeature = "Geo.Mean"

    # both error bars
    def testErrorBars(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xerror_low = "/SD"
        self.view.xerror_high = "*SD"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yerror_low = "/SD"
        self.view.yerror_high = "*SD"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
    # x error statistic
    def testXErrorBars(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xerror_low = "/SD"
        self.view.xerror_high = "*SD"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
    # y error statistic
    def testYErrorBars(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yerror_low = "/SD"
        self.view.yerror_high = "*SD"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    # x scale
    def testXScaleLog(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xscale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    def testXScaleLogicle(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xscale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
            
    # y scale
    def testYScaleLog(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yscale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    def testYScaleLogicle(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yscale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
    # both scales
    def testScaleLogLog(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xscale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yscale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    def testScaleLogicleLogicle(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.xscale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yscale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    
    def testPlotParams(self):
        super().testPlotParams()
        
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.xlim = (0, 1000)
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
        
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.ylim = (0, 1000)
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    
