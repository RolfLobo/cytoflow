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
cytoflow.views.stats_1d
-----------------------

Plot a statistic with a numeric variable on the X axis.

`Stats1DView` -- the `IView` class that makes the plot.
"""

from traits.api import provides, Constant
import matplotlib as mpl
import matplotlib.pyplot as plt

import numpy as np

import cytoflow.utility as util
from .i_view import IView
from .base_views import Base1DStatisticsView

@provides(IView)
class Stats1DView(Base1DStatisticsView):
    """
    Plot a statistic.  The value of the statistic will be plotted on the
    Y axis; a numeric conditioning variable must be chosen for the X axis.
    Every variable in the statistic must be specified as either the `variable`
    or one of the plot facets.
    
    Attributes
    ----------
    variable_scale : {'linear', 'log', 'logicle'}
        The scale applied to the variable (on the X axis)
        
    Examples
    --------
    
    .. plot::
        :context: close-figs
        
        Make a little data set.
    
        >>> import cytoflow as flow
        >>> import_op = flow.ImportOp()
        >>> import_op.tubes = [flow.Tube(file = "Plate01/RFP_Well_A3.fcs",
        ...                              conditions = {'Dox' : 10.0}),
        ...                    flow.Tube(file = "Plate01/CFP_Well_A4.fcs",
        ...                              conditions = {'Dox' : 1.0})]
        >>> import_op.conditions = {'Dox' : 'float'}
        >>> ex = import_op.apply()
    
    Create and a new statistic.
    
    .. plot::
        :context: close-figs
        
        >>> ch_op = flow.ChannelStatisticOp(name = 'MeanByDox',
        ...                                 channel = 'Y2-A',
        ...                                 function = flow.geom_mean,
        ...                                 by = ['Dox'])
        >>> ex2 = ch_op.apply(ex)
        
    View the new statistic
    
    .. plot::
        :context: close-figs
        
        >>> flow.Stats1DView(variable = 'Dox',
        ...                  statistic = 'MeanByDox', 
        ...                  feature = 'Y2-A',
        ...                  variable_scale = 'log',
        ...                  scale = 'log').plot(ex2)
    """
    
    # traits   
    id = Constant("cytoflow.view.stats1d")
    friendly_id = Constant("1D Statistics View")
    
    variable_scale = util.ScaleEnum
    
    def enum_plots(self, experiment):
        """
        Returns an iterator over the possible plots that this View can
        produce.  The values returned can be passed to `plot`.
        """
                
        return super().enum_plots(experiment)
        
    
    def plot(self, experiment, plot_name = None, **kwargs):
        """Plot a chart of a variable's values against a statistic.
        
        Parameters
        ----------
        
        variable_lim : (float, float)
            The limits on the variable axis
        
        color : a matplotlib color
            The color to plot with.  Overridden if `huefacet` is not `None`
            
        linewidth : float
            The width of the line, in points
            
        linestyle : ['solid' | 'dashed', 'dashdot', 'dotted' | (offset, on-off-dash-seq) | '-' | '--' | '-.' | ':' | 'None' | ' ' | '']
            
        marker : a matplotlib marker style
            See http://matplotlib.org/api/markers_api.html#module-matplotlib.markers
            
        markersize : int
            The marker size in points
            
        markerfacecolor : a matplotlib color
            The color to make the markers.  Overridden (?) if `huefacet` is not `None`
            
        alpha : the alpha blending value, from 0.0 (transparent) to 1.0 (opaque)
        
        capsize : scalar
            The size of the error bar caps, in points
            
        shade_error : bool
            If `False` (the default), plot the error statistic as traditional 
            "error bars."  If `True`, plot error statistic as a filled, shaded
            region.
            
        shade_alpha : float
            The transparency of the shaded error region, from 0.0 (transparent)
            to 1.0 (opaque.)  Default is 0.2.
        
        Notes
        -----
                
        Other ``kwargs`` are passed to `matplotlib.pyplot.plot`
        
        """

        if experiment is None:
            raise util.CytoflowViewError('experiment', "No experiment specified")
        
        if self.variable not in experiment.conditions:
            raise util.CytoflowError('variable',
                                     "Variable {} not in the experiment"
                                     .format(self.variable))
        
        if not util.is_numeric(experiment[self.variable]):
            raise util.CytoflowError('variable',
                                     "Variable {} must be numeric"
                                     .format(self.variable))
        
        variable_scale = util.scale_factory(self.variable_scale, 
                                            experiment, 
                                            condition = self.variable)
        
        super().plot(experiment, 
                     plot_name, 
                     variable_scale = variable_scale,
                     **kwargs)

    def _grid_plot(self, experiment, grid, **kwargs):

        data = grid.data
        data_scale = kwargs.pop('scale')
        variable_scale = kwargs.pop('variable_scale')
        
        variable_lim = kwargs.pop("variable_lim", None)
        if variable_lim is None:
            variable_lim = (variable_scale.clip(data[self.variable].min() * 0.9),
                            variable_scale.clip(data[self.variable].max() * 1.1))
                      
        lim = kwargs.pop("lim", None)
        if lim is None:
            
            lim = (data[self.feature].min(), data[self.feature].max())
            if self.error_low and self.error_high:
                lim = (data[self.error_low].min(), data[self.error_high].max())
            
            span = lim[1] - lim[0]
            lim = (lim[0] - 0.05 * span, lim[1] + 0.05 * span)
            lim = (data_scale.clip(lim[0]), data_scale.clip(lim[1]))
                        
        orientation = kwargs.pop('orientation', 'vertical')
        capsize = kwargs.pop('capsize', None)
        shade_error = kwargs.pop('shade_error', False)
        shade_alpha = kwargs.pop('shade_alpha', 0.2)
        
        if orientation == 'vertical':
            # plot the error bars first so the axis labels don't get overwritten
            if self.error_low:
                if shade_error:
                    grid.map(_v_error_shade, self.variable, self.feature, self.error_low, self.error_high, alpha = shade_alpha)
                else:
                    grid.map(_v_error_bars, self.variable, self.feature, self.error_low, self.error_high, capsize = capsize)
            
            grid.map(plt.plot, self.variable, self.feature, **kwargs)
            
            return dict(xscale = variable_scale,
                        xlim = variable_lim,
                        yscale = data_scale, 
                        ylim = lim)
        else:
            # plot the error bars first so the axis labels don't get overwritten
            if self.error_low:
                if shade_error:
                    grid.map(_h_error_shade, self.feature, self.variable, self.error_low, self.error_high, alpha = shade_alpha)
                else:
                    grid.map(_h_error_bars, self.feature, self.variable, self.error_low, self.error_high, capsize = capsize)
            
            grid.map(plt.plot, self.feature, self.variable, **kwargs)
            
            return dict(yscale = variable_scale,
                        ylim = variable_lim,
                        xscale = data_scale, 
                        xlim = lim)

                
def _v_error_bars(x, y, yerr_low, yerr_high, ax = None, color = None, errwidth = None, capsize = None, **kwargs):
    
    if errwidth is not None:
        kwargs.setdefault("lw", errwidth)
    else:
        kwargs.setdefault("lw", mpl.rcParams["lines.linewidth"])
        
    if capsize is not None:
        kwargs['marker'] = '_'
        kwargs['markersize'] = capsize * 2
        kwargs['markeredgewidth'] = kwargs['lw']
        
    for x_i, lo_i, hi_i in zip(x, yerr_low, yerr_high):
        plt.plot((x_i, x_i), (lo_i, hi_i), color = color, **kwargs)


def _v_error_shade(x, _, yerr_low, yerr_high, ax = None, color = None, alpha = None, **kwargs):
    plt.fill_between(x.to_list(), yerr_low.to_list(), yerr_high.to_list(), color = color, alpha = alpha, **kwargs)


def _h_error_bars(x, y, xerr_low, xerr_high, ax = None, color = None, errwidth = None, capsize = None, **kwargs):

    
    if errwidth is not None:
        kwargs.setdefault("lw", errwidth)
    else:
        kwargs.setdefault("lw", mpl.rcParams["lines.linewidth"])

    if capsize is not None:
        kwargs['marker'] = '|'
        kwargs['markersize'] = capsize * 2
        kwargs['markeredgewidth'] = kwargs['lw']

    for y_i, lo_i, hi_i in zip(y, xerr_low, xerr_high):
        plt.plot((lo_i, hi_i), (y_i, y_i), color = color, **kwargs)
        
    
def _h_error_shade(x, y, xerr_low, xerr_high, ax = None, color = None, alpha = None, **kwargs):
    plt.fill_betweenx(y.to_list(), xerr_low.to_list(), xerr_high.to_list(), color = color, alpha = alpha)
    
util.expand_class_attributes(Stats1DView)
util.expand_method_parameters(Stats1DView, Stats1DView.plot)
    

if __name__ == '__main__':
    import cytoflow as flow
    
    tube1 = flow.Tube(file = '../../cytoflow/tests/data/Plate01/RFP_Well_A3.fcs',
                      conditions = {"Dox" : 10.0})
    
    tube2 = flow.Tube(file = '../../cytoflow/tests/data/Plate01/CFP_Well_A4.fcs',
                      conditions = {"Dox" : 1.0})                      

    ex = flow.ImportOp(conditions = {"Dox" : "float"}, tubes = [tube1, tube2])
    
    thresh = flow.ThresholdOp()
    thresh.name = "Y2-A+"
    thresh.channel = 'Y2-A'
    thresh.threshold = 2005.0

    ex2 = thresh.apply(ex)
    
    s = flow.Stats1DView()
    s.by = "Dox"
    s.ychannel = "Y2-A"
    s.yfunction = np.mean
    s.huefacet = "Y2-A+"
    
    plt.ioff()
    s.plot(ex2)
    plt.show()
