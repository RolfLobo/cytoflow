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
cytoflow.operations.mst
-----------------------

Apply a polygon gate to a minimum spanning tree.  
`mst` has two classes:

`ConditionSelectionOp` -- Applies a gate to a (categorical) condition, creating
    a new (boolean) condition that is ``True`` if the event's value for the
    categorical condition is in the ``values`` attribute.

`MSTOp` -- Applies a gate based on a polygon drawn on an MST.

`MSTSelectionView` -- an `IView` that allows you to view the 
polygon and/or interactively set the vertices on an MST.
"""

from warnings import warn

from traits.api import (Str, List, Float, provides, Instance, Bool, observe, 
                        Any, Dict, Constant, HasTraits, Int)

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.widgets import PolygonSelector
import numpy as np

import cytoflow.utility as util
from cytoflow.views import MSTView

from .i_operation import IOperation

@provides(IOperation)
class ConditionSelectionOp(HasTraits):
    """
    Apply a gate to a categorical condition. Creates a new boolean condition
    named `name`, which is ``True`` if the event's value for `condition` is
    in `condition_values`.
    
    Attributes
    ----------
    name : Str
        The operation name.  Used to name the new metadata field in the
        experiment that's created by `apply`
        
    condition : Str
        The condition to apply the gate to.
        
    condition_values : List(Any)
        The values for which to set the new `name` condition to ``True``.
        
    Notes
    -----
    This is intended to be a base class for `MSTOp`. I'm not sure if it will
    be useful for additional derived classes, but I figured I'd architect it
    to make that straightforward.

    """
    
    name = Str
    condition = Str
    condition_values = List(Any)
        
    def apply(self, experiment):
        """Applies the gate to an experiment.
        
        Parameters
        ----------
        experiment : Experiment
            the old `Experiment` to which this op is applied
            
        Returns
        -------
        Experiment
            a new 'Experiment`, the same as ``experiment`` but with 
            a new column of type `bool` with the same as the operation name.  
            The bool is ``True`` if the event's value of the `condition` 
            condition is in `condition_values`, and ``False`` otherwise.
            
        Raises
        ------
        CytoflowOpError
            if for some reason the operation can't be applied to this
            experiment. The reason is in the ``args`` attribute.
        """
        
        if experiment is None:
            raise util.CytoflowOpError('experiment',
                                       "No experiment specified")
            
        # make sure name got set!
        if not self.name:
            raise util.CytoflowOpError('name',
                                       "You have to set the gate's name "
                                       "before applying it!")

        if self.name in experiment.data.columns:
            raise util.CytoflowOpError('name',
                                       "{} is in the experiment already!"
                                       .format(self.name))
            
        if self.name != util.sanitize_identifier(self.name):
            raise util.CytoflowOpError('name',
                                       "Name can only contain letters, numbers and underscores."
                                       .format(self.name)) 
            
        if self.condition not in experiment.data.columns:
            raise util.CytoflowOpError('condition',
                                       "'condition' must be a condition in the experiment.")
            
        if self.condition not in experiment.conditions:
            raise util.CytoflowOpError('condition',
                                       "'condition' must be a condition in the experiment.")
        
        in_selection = experiment[self.condition].apply(lambda x: x in self.condition_values)
        if not in_selection.any():
            warn("No events were in the gate -- is this what you intended?",
                 util.CytoflowOpWarning)
        
        new_experiment = experiment.clone(deep = False)        
        new_experiment.add_condition(self.name, "bool", in_selection)
        new_experiment.history.append(self.clone_traits(transient = lambda _: True))
            
        return new_experiment
    
@provides(IOperation)
class MSTOp(ConditionSelectionOp):
    """
    Apply a gate to a polygon drawn around a minimum spanning tree.
    
    The only attribute is `name` -- everything else is set by the default view,
    which inherits `MSTView`.
    
    Attributes
    ----------
    """
    
    id = Constant('cytoflow.operation.mst')
    friendly_id = Constant("Minimum Spanning Tree")
    
    _selection_view = Instance('MSTSelectionView', transient = True)
    
    def apply(self, experiment):
        
        return super().apply(experiment)

    
    def default_view(self, **kwargs):
        """
        Returns an `IView` that allows a user to view the polygon or interactively draw it.

        """ 

        self._selection_view = MSTSelectionView(op = self)
        self._selection_view.trait_set(**kwargs)
        return self._selection_view
    
util.expand_class_attributes(MSTOp)
    
class MSTSelectionView(MSTView):
    """
    Attributes
    ----------
    op : Instance(`IOperation`)
        The `IOperation` that this view is associated with.  If you
        created the view using `default_view`, this is already set.
    """
    
    id = Constant('cytoflow.view.mst_selection')
    friendly_id = Constant("Minimum Spanning Tree")
    
    
    op = Instance(IOperation)
    interactive = Bool(False, transient = True)

    # internal state.
    _ax = Any(transient = True)
    _widget = Instance(PolygonSelector, transient = True)
    _polygon = List((Float, Float))
    _patch = Instance(mpl.patches.PathPatch, transient = True)
    _patch_props = Dict()
    _in = List

    def plot(self, experiment, **kwargs):
        self._patch_props = kwargs.pop('patch_props',
                                        {'edgecolor' : 'black',
                                         'linewidth' : 2,
                                         'fill' : False})
        
        super().plot(experiment, **kwargs)
        self._ax = plt.gca()
        self._draw_poly(None)
        self._interactive(None)


    @observe('_polygon', post_init = True)        
    def _draw_poly(self, _):
        if not self._polygon or len(self._polygon) < 3:
            return
               
        polygon_path = mpl.path.Path(np.concatenate((np.array(self._polygon), 
                                                     np.array((0,0), ndmin = 2))),
                                     closed = True) 
        
        cv = []
        for v, g in zip(self._vertices, self._groups):
            if polygon_path.contains_point(v):
                cv.append(g)

        self.op.condition = self._loc_level
        self.op.condition_values = cv
        
        if not self._ax:
            return

        if self._patch and self._patch in self._ax.patches:
            self._patch.remove()

        self._patch = mpl.patches.PathPatch(polygon_path, **self._patch_props)

        self._ax.add_patch(self._patch)
        plt.draw()

    @observe('interactive', post_init = True)
    def _interactive(self, _):
        if self._ax and self.interactive:
            self._widget = PolygonSelector(self._ax,
                                           self._onselect,
                                           useblit = True,
                                           grab_range = 20)
        elif self._widget:
            self._widget.set_active(False) 
            self._widget = None    

    def _onselect(self, vertices):
        self._polygon = vertices
        self.interactive = False
        
util.expand_class_attributes(MSTSelectionView)
util.expand_method_parameters(MSTSelectionView, MSTSelectionView.plot)
