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
Created on Jan 5, 2018

@author: brian
'''

import os, unittest, tempfile
import pandas as pd  # @UnusedImport, to shut up exec() below

# needed for testing lambdas
from cytoflow import geom_mean, geom_sd  # @UnusedImport

from cytoflowgui.tests.test_base import ImportedDataTest
from cytoflowgui.workflow.views.matrix import MatrixWorkflowView, MatrixPlotParams
from cytoflowgui.workflow.serialization import load_yaml, save_yaml
from cytoflowgui.workflow.subset import RangeSubset

class TestMatrix(ImportedDataTest):
    
    def setUp(self):
        super().setUp()
        
        self.addTypeEqualityFunc(MatrixWorkflowView, 'assertHasTraitsEqual')
        self.addTypeEqualityFunc(MatrixPlotParams, 'assertHasTraitsEqual')

        self.wi = wi = self.workflow.workflow[-1]
        self.view = view = MatrixWorkflowView()
        wi.views.append(view)
        wi.current_view = view
        
        self.view.xfacet = "Dox"
        self.view.yfacet = "IP"
        self.view.statistic = "GeoMeanByDoxIP"
        self.view.feature = "Geo.Mean"     
        self.workflow.selected = wi
        self.workflow.wi_waitfor(self.wi, 'view_error', '')

    def testHeat(self):
        pass
    
    def testPie(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = ""
        self.view.variable = "IP"
        self.view.style = "pie"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')  
    
    def testPetal(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = ""
        self.view.variable = "IP"
        self.view.style = "petal"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')  
    
    def testScaleByEvents(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.scale_by_events = True
        self.workflow.wi_waitfor(self.wi, 'view_error', '')  
    
    def testPieScaleByEvents(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = ""
        self.view.variable = "IP"
        self.view.style = "pie"
        self.view.scale_by_events = True
        self.workflow.wi_waitfor(self.wi, 'view_error', '')  
    
    def testPetalScaleByEvents(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.yfacet = ""
        self.view.variable = "IP"
        self.view.style = "petal"
        self.view.scale_by_events = True
        self.workflow.wi_waitfor(self.wi, 'view_error', '')  
    
    # scale
    def testScaleLog(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.scale = "log"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')        
    
    def testScaleLogicle(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.scale = "logicle"
        self.workflow.wi_waitfor(self.wi, 'view_error', '')  
    
    # subset
    def testSubset(self):
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
    
        self.view.subset_list.append(RangeSubset(name = "Dox",
                                                 values = [1.0, 10.0, 100.0]))
        self.view.subset_list[0].low = 10.0
        self.view.subset_list[0].high = 100.0
    
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
    
        # legendlabel
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.legendlabel = "Legend label"
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
    
        # palette
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.palette = 'flare'
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
        # legend
        self.workflow.wi_sync(self.wi, 'view_error', 'waiting')
        self.view.plot_params.legend = False
        self.workflow.wi_waitfor(self.wi, 'view_error', '')
    
    
    def testSerialize(self):
        fh, filename = tempfile.mkstemp()
        try:
            os.close(fh)
    
            save_yaml(self.view, filename)
            new_view = load_yaml(filename)
        finally:
            os.unlink(filename)
    
        self.maxDiff = None
    
        self.assertEqual(self.view, new_view)
    
    def testSerializeWorkflowItem(self):
        fh, filename = tempfile.mkstemp()
        try:
            os.close(fh)
    
            save_yaml(self.wi, filename)
            new_wi = load_yaml(filename)
    
        finally:
            os.unlink(filename)
    
        self.maxDiff = None
    
        self.assertEqual(self.wi, new_wi)
    
    def testNotebook(self):
        code = "import cytoflow as flow\n"
        for i, wi in enumerate(self.workflow.workflow):
            code = code + wi.operation.get_notebook_code(i)
    
            for view in wi.views:
                code = code + view.get_notebook_code(i)
    
        exec(code) # smoke test


if __name__ == "__main__":
#     import sys;sys.argv = ['', 'TestStats1D.testSerialize']
#     import sys;sys.argv = ['', 'TestStats1D.testSerializeWorkflowItemV1']
    unittest.main()
