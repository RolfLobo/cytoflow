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

#!/usr/bin/env python3.8

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
cytoflowgui.workflow.views.density
----------------------------------

"""

from textwrap import dedent

from traits.api import provides, Bool, Instance

from cytoflow import DensityView
import cytoflow.utility as util

from cytoflowgui.workflow.serialization import camel_registry, cytoflow_class_repr, traits_str
from .view_base import IWorkflowView, WorkflowFacetView, Data2DPlotParams

DensityView.__repr__ = cytoflow_class_repr

     
class DensityPlotParams(Data2DPlotParams):
    gridsize = util.PositiveCInt(50, allow_zero = False)
    smoothed = Bool(False)
    smoothed_sigma = util.PositiveCFloat(1.0, allow_zero = False)
    
    
@provides(IWorkflowView)
class DensityWorkflowView(WorkflowFacetView, DensityView):
    plot_params = Instance(DensityPlotParams, ())
            
    def get_notebook_code(self, idx):
        view = DensityView()
        view.copy_traits(self, view.copyable_trait_names())
        plot_params_str = traits_str(self.plot_params)

        return dedent("""
        {repr}.plot(ex_{idx}{plot}{plot_params})
        """
        .format(repr = repr(view),
                idx = idx,
                plot = ".subset(" + repr(self.plotfacet) + ", " + repr(self.current_plot) + ")" if self.current_plot else "",
                plot_params = ", " + plot_params_str if plot_params_str else ""))
        
 
### Serialization
@camel_registry.dumper(DensityWorkflowView, 'density-view', version = 2)
def _dump(view):
    return dict(xchannel = view.xchannel,
                xscale = view.xscale,
                ychannel = view.ychannel,
                yscale = view.yscale,
                xfacet = view.xfacet,
                yfacet = view.yfacet,
                huescale = view.huescale,
                plotfacet = view.plotfacet,
                subset_list = view.subset_list,
                plot_params = view.plot_params,
                current_plot = view.current_plot)
    
    
@camel_registry.dumper(DensityWorkflowView, 'density-view', version = 1)
def _dump_v1(view):
    return dict(xchannel = view.xchannel,
                xscale = view.xscale,
                ychannel = view.ychannel,
                yscale = view.yscale,
                xfacet = view.xfacet,
                yfacet = view.yfacet,
                huescale = view.huescale,
                plotfacet = view.plotfacet,
                subset_list = view.subset_list)
    
    
@camel_registry.dumper(DensityPlotParams, 'density-view-params', version = 1)
def _dump_params(params):
    return dict(
                # BasePlotParams
                title = params.title,
                xlabel = params.xlabel,
                ylabel = params.ylabel,
                huelabel = params.huelabel,
                col_wrap = params.col_wrap,
                sns_style = params.sns_style,
                sns_context = params.sns_context,
                legend = params.legend,
                sharex = params.sharex,
                sharey = params.sharey,
                despine = params.despine,

                # DataplotParams
                min_quantile = params.min_quantile,
                max_quantile = params.max_quantile,
                
                # Data2DPlotParams
                xlim = params.xlim,
                ylim = params.ylim,
                
                # Density
                gridsize = params.gridsize,
                smoothed = params.smoothed,
                smoothed_sigma = params.smoothed_sigma )
    
    
@camel_registry.loader('density-view', version = any)
def _load(data, version):
    return DensityWorkflowView(**data)


@camel_registry.loader('density-view-params', version = any)
def _load_params(data, version):
    return DensityPlotParams(**data)

