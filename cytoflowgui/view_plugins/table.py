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

"""
Table
-----

Make a table out of a statistic.  The table can then be exported.

.. object:: Statistic

    Which statistic to view.
    
.. object:: Feature
        The column in the statistic to view (often a channel name.)
    
.. object:: Rows

    Which variable to use for the rows

.. object:: Subrows

    Which variable to use for subrows.
    
.. object:: Columns

    Which variable to use for the columns.
    
.. object:: Subcolumns

    Which variable to use for the subcolumns.
    
.. object:: Export

    Export the table to a CSV file.

    
.. plot::
   :include-source: False

    import cytoflow as flow
    import_op = flow.ImportOp()
    import_op.tubes = [flow.Tube(file = "Plate01/RFP_Well_A3.fcs",
                                 conditions = {'Dox' : 10.0}),
                       flow.Tube(file = "Plate01/CFP_Well_A4.fcs",
                                 conditions = {'Dox' : 1.0})]
    import_op.conditions = {'Dox' : 'float'}
    ex = import_op.apply()
    
    ex2 = flow.ThresholdOp(name = 'Threshold',
                           channel = 'Y2-A',
                           threshold = 2000).apply(ex)
    

    ex3 = flow.ChannelStatisticOp(name = "ByDox",
                                  channel = "Y2-A",
                                  by = ['Dox', 'Threshold'],
                                  function = len).apply(ex2) 

    flow.TableView(statistic = "ByDox",
                   feature = "Y2-A",
                   row_facet = "Dox",
                   column_facet = "Threshold").plot(ex3)    

"""

import pandas as pd

from traits.api import provides, Property, Event, observe, List
from traitsui.api import View, Item, EnumEditor, VGroup, ButtonEditor
from envisage.api import Plugin
from pyface.api import ImageResource, FileDialog, OK  # @UnresolvedImport

from ..workflow.views import TableWorkflowView
from ..util import DefaultFileDialog
from ..editors import SubsetListEditor, ColorTextEditor, ExtendableEnumEditor, InstanceHandlerEditor
from ..subset_controllers import subset_handler_factory

from .i_view_plugin import IViewPlugin, VIEW_PLUGIN_EXT
from .view_plugin_base import ViewHandler, PluginHelpMixin

    
class TableHandler(ViewHandler):

    indices = Property(depends_on = "context.statistics, model.statistic, model.subset")
    levels = Property(depends_on = "context.statistics, model.statistic")
    features = Property(depends_on = "context.statistics, model.statistic")

    export = Event()

    view_traits_view = \
        View(VGroup(
             VGroup(Item('statistic',
                         editor = EnumEditor(name='context_handler.statistics_names'),
                         label = "Statistic"),
                    Item('feature',
                         editor = EnumEditor(name = 'handler.features'),
                         label = "Feature"),
                    Item('row_facet',
                         editor = ExtendableEnumEditor(name='handler.indices',
                                                     extra_items = {"None" : ""}),
                         label = "Rows"),
                    Item('subrow_facet',
                         editor = ExtendableEnumEditor(name='handler.indices',
                                                     extra_items = {"None" : ""}),
                         label = "Subrows"),
                    Item('column_facet',
                         editor = ExtendableEnumEditor(name='handler.indices',
                                                     extra_items = {"None" : ""}),
                         label = "Columns"),
                    Item('subcolumn_facet',
                         editor = ExtendableEnumEditor(name='handler.indices',
                                                     extra_items = {"None" : ""}),
                         label = "Subcolumn"),
                    Item('handler.export',
                         editor = ButtonEditor(label = "Export..."),
                         enabled_when = 'result is not None',
                         show_label = False),
                    label = "Table View",
                    show_border = False),
             VGroup(Item('subset_list',
                         show_label = False,
                         editor = SubsetListEditor(conditions = "handler.levels",
                                                   editor = InstanceHandlerEditor(view = 'subset_view',
                                                                                  handler_factory = subset_handler_factory),
                                                   mutable = False)),
                    label = "Subset",
                    show_border = False,
                    show_labels = False),
             Item('context.view_warning',
                  resizable = True,
                  visible_when = 'context.view_warning',
                  editor = ColorTextEditor(foreground_color = "#000000",
                                          background_color = "#ffff99")),
             Item('context.view_error',
                  resizable = True,
                  visible_when = 'context.view_error',
                  editor = ColorTextEditor(foreground_color = "#000000",
                                           background_color = "#ff9191"))))
        
    view_params_view = View() # empty view -- no parameters for a table view
        
    # MAGIC: gets the value for the property indices
    def _get_indices(self):
        if not (self.context and self.context.statistics 
                and self.model.statistic in self.context.statistics):
            return []
        
        stat = self.context.statistics[self.model.statistic]
        data = pd.DataFrame(index = stat.index)
        
        if self.model.subset:
            data = data.query(self.model.subset)
            
        if len(data) == 0:
            return []       
        
        names = list(data.index.names)
        for name in names:
            unique_values = data.index.get_level_values(name).unique()
            if len(unique_values) == 1:
                data.index = data.index.droplevel(name)
        
        return list(data.index.names)
    
    # MAGIC: gets the value for the property 'levels'
    # returns a Dict(Str, pd.Series)
    def _get_levels(self):        
        if not (self.context and self.context.statistics 
                and self.model.statistic in self.context.statistics):
            return {}
        
        stat = self.context.statistics[self.model.statistic]
        index = stat.index
        
        names = list(index.names)
        for name in names:
            unique_values = index.get_level_values(name).unique()
            if len(unique_values) == 1:
                index = index.droplevel(name)

        names = list(index.names)
        ret = {}
        for name in names:
            ret[name] = pd.Series(index.get_level_values(name)).sort_values()
            ret[name] = pd.Series(ret[name].unique())
            
        return ret
    
    # MAGIC: gets the value for the property "features"
    def _get_features(self):
        if not (self.context and self.context.statistics 
                and self.model.statistic in self.context.statistics):
            return []
         
        stat = self.context.statistics[self.model.statistic]
        return stat.columns.to_list()
    
    @observe('export')
    def _on_export(self, _):
         
        dialog = DefaultFileDialog(parent = None,
                                   action = 'save as', 
                                   default_suffix = "csv",
                                   wildcard = (FileDialog.create_wildcard("CSV", "*.csv") + ';' + #@UndefinedVariable  
                                               FileDialog.create_wildcard("All files", "*")))     #@UndefinedVariable  
 
        if dialog.open() != OK:
            return
         
        self.model._export_data(self.model.result, self.model.feature, dialog.path)
            
                    


@provides(IViewPlugin)
class TablePlugin(Plugin, PluginHelpMixin):

    id = 'cytoflowgui.view.table'
    view_id = 'cytoflow.view.table'
    name = "Table View"
    
    def get_view(self):
        return TableWorkflowView()
    
    def get_handler(self, model, context):
        if isinstance(model, TableWorkflowView):
            return TableHandler(model = model, context = context)
        else:
            return None

    def get_icon(self):
        return ImageResource('table')

    plugin = List(contributes_to = VIEW_PLUGIN_EXT)
    def _plugin_default(self):
        return [self]
    

