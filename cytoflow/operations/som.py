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
cytoflow.operations.som
-----------------------

Use self-organizing maps to cluster events in any number of dimensions.
`som` has one classes:

`SOMOp` -- the `IOperation` to perform the clustering.

"""


from traits.api import (HasStrictTraits, Str, Dict, Any, Instance, 
                        Constant, List, Int, Float, provides)

import numpy as np
import pandas as pd

# have to use importlib because the package name has a hyphen :(
import importlib
som = importlib.import_module("sklearn-som.sklearn_som.som")

from cytoflow.views import IView, HistogramView, ScatterplotView
import cytoflow.utility as util

from .i_operation import IOperation
from .base_op_views import By1DView, By2DView, AnnotatingView

@provides(IOperation)
class SOMOp(HasStrictTraits):
    """
    Use a self-organizing map to cluster events.  
    
    Call `estimate` to create the map, often using a random subset of the
    events that will eventually be clustered.
      
    Calling `apply` creates a new categorical metadata variable 
    named `name`, with possible values ``{name}_1`` .... ``name_n`` where 
    ``n`` is the product of the height and width of the map.

    The same model may not be appropriate for different subsets of the data set.
    If this is the case, you can use the `by` attribute to specify 
    metadata by which to aggregate the data before estimating (and applying) a 
    model.  The  number of clusters (and other clustering parameters) is the 
    same across each subset, though.

    Attributes
    ----------
    name : Str
        The operation name; determines the name of the new metadata column
        
    channels : List(Str)
        The channels to apply the clustering algorithm to.

    scale : Dict(Str : {"linear", "logicle", "log"})
        Re-scale the data in the specified channels before fitting.  If a 
        channel is in `channels` but not in `scale`, the current 
        package-wide default (set with `set_default_scale`) is used.
    
        .. note::
           Sometimes you may see events labeled ``{name}_None`` -- this results 
           from events for which the selected scale is invalid. For example, if
           an event has a negative measurement in a channel and that channel's
           scale is set to "log", this event will be set to ``{name}_None``.

    width : Int (default = 10)
        What is the width of the map? The number of clusters used is the product
        of ``width`` and ``height``.
        
    height : Int (default = 10)
        What is the height of the map? The number of clusters used is the product
        of ``width`` and ``height``.
        
    learning_rate : Float (default = 1.0)
        The initial step size for updating SOM weights. Changes as the map is
        learned.
        
    sigma : Float (default = 1.0)
        The magnitude of each update. Fixed over the course of the run -- 
        higher values mean more aggressive updates.
        
    max_iterations : Int (default = 3000)
        The maximum number of update steps to take before learning stops.
    
    by : List(Str)
        A list of metadata attributes to aggregate the data before estimating
        the model.  For example, if the experiment has two pieces of metadata,
        ``Time`` and ``Dox``, setting `by` to ``["Time", "Dox"]`` will 
        fit the model separately to each subset of the data with a unique 
        combination of ``Time`` and ``Dox``.
        
    sample : Float (default = 0.01)
        What proportion of the data set to use for training? Defaults to 1%
        of the dataset to help with runtime.
        
    
    Notes
    -----
    
    Uses SOM code from https://github.com/rileypsmith/sklearn-som -- thanks!
    
    If you'd like to learn more about self-organizing maps and how to use
    them effectively, check out https://rubikscode.net/2018/08/20/introduction-to-self-organizing-maps/
      
    
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
    
    Create and parameterize the operation.
    
    .. plot::
        :context: close-figs
        
        >>> som_op = flow.SOMOp(name = 'SOM',
        ...                     channels = ['V2-A', 'Y2-A'],
        ...                     scale = {'V2-A' : 'log',
        ...                              'Y2-A' : 'log'})
        
    Estimate the clusters
    
    .. plot::
        :context: close-figs
        
        >>> som_op.estimate(ex)
        
    Plot a diagnostic view
    
    .. plot::
        :context: close-figs
        
        >>> som_op.default_view().plot(ex)

    Apply the gate
    
    .. plot::
        :context: close-figs
        
        >>> ex2 = som_op.apply(ex)

    Plot a diagnostic view with the event assignments
    
    .. plot::
        :context: close-figs
        
        >>> km_op.default_view().plot(ex2)
    """
    
    id = Constant('edu.mit.synbio.cytoflow.operations.som')
    friendly_id = Constant("Self Organizing Maps Clustering")
    
    name = Str
    channels = List(Str)
    scale = Dict(Str, util.ScaleEnum)
    width = Int(10)
    height = Int(10)
    learning_rate = Float(1.0)
    sigma = Float(1.0)
    max_iterations = Int(3000)
    by = List(Str)
    sample = util.UnitFloat(0.01)
    
    _som = Dict(Any, Instance("sklearn-som.sklearn_som.som.SOM"), transient = True)
    _scale = Dict(Str, Instance(util.IScale), transient = True)
    
    def estimate(self, experiment, subset = None):
        """
        Estimate the self-organized map
        
        Parameters
        ----------
        experiment : Experiment
            The `Experiment` to use to estimate the k-means clusters
            
        subset : str (default = None)
            A Python expression that specifies a subset of the data in 
            ``experiment`` to use to parameterize the operation.
        """

        if experiment is None:
            raise util.CytoflowOpError('experiment',
                                       "No experiment specified")
        
        if self.width < 1:
            raise util.CytoflowOpError('width',
                                       "width must be >= 1")
            
        if self.height < 1:
            raise util.CytoflowOpError('height',
                                       "height must be >= 1")
            
        if self.learning_rate <= 0:
            raise util.CytoflowOpError('learning_rate',
                                       "learning_rate must be > 0")
            
        if self.sigma < 0:
            raise util.CytoflowOpError('sigma',
                                       "sigma must be >= 0")
            
        if self.learning_rate <= 0:
            raise util.CytoflowOpError('learning_rate',
                                       "learning_rate must be > 0")
            
        if self.max_iterations < 1:
            raise util.CytoflowOpError('max_iterations',
                                       "max_iterations must be >= 1")
            
        if self.sample <= 0:
            raise util.CytoflowOpError('sample',
                                       "sample must be > 0")
        
        if len(self.channels) == 0:
            raise util.CytoflowOpError('channels',
                                       "Must set at least one channel")
            
        if len(self.channels) != len(set(self.channels)):
            raise util.CytoflowOpError('channels', 
                                       "Must not duplicate channels")

        for c in self.channels:
            if c not in experiment.data:
                raise util.CytoflowOpError('channels',
                                           "Channel {0} not found in the experiment"
                                      .format(c))
                
        for c in self.scale:
            if c not in self.channels:
                raise util.CytoflowOpError('scale',
                                           "Scale set for channel {0}, but it isn't "
                                           "in the experiment"
                                           .format(c))
       
        for b in self.by:
            if b not in experiment.data:
                raise util.CytoflowOpError('by',
                                           "Aggregation metadata {} not found, "
                                           "must be one of {}"
                                           .format(b, experiment.conditions))

        if subset:
            try:
                experiment = experiment.query(subset)
            except:
                raise util.CytoflowOpError('subset',
                                            "Subset string '{0}' isn't valid"
                                            .format(subset))
                
            if len(experiment) == 0:
                raise util.CytoflowOpError('subset',
                                           "Subset string '{0}' returned no events"
                                           .format(subset))
                
        if self.by:
            groupby = experiment.data.groupby(self.by, observed = True)
        else:
            # use a lambda expression to return a group that contains
            # all the events
            groupby = experiment.data.groupby(lambda _: True, observed = True)
            
        # get the scale. estimate the scale params for the ENTIRE data set,
        # not subsets we get from groupby().  And we need to save it so that
        # the data is transformed the same way when we apply()
        self._scale = {}
        for c in self.channels:
            if c in self.scale:
                self._scale[c] = util.scale_factory(self.scale[c], experiment, channel = c)
            else:
                self._scale[c] = util.scale_factory(util.get_default_scale(), experiment, channel = c)
                    
                    
        soms = {}
        for group, data_subset in groupby:
            if len(data_subset) == 0:
                raise util.CytoflowOpError('by',
                                           "Group {} had no data"
                                           .format(group))
            x = data_subset.sample(frac = self.sample).loc[:, self.channels[:]]
            for c in self.channels:
                x[c] = self._scale[c](x[c])
            
            # drop data that isn't in the scale range
            for c in self.channels:
                x = x[~(np.isnan(x[c]))]
            x = x.values
            
            soms[group] = som.SOM(m = self.height,
                                 n = self.width,
                                 dim = len(self.channels),
                                 lr = self.learning_rate,
                                 sigma = self.sigma,
                                 max_iter = self.max_iterations)
            
            soms[group].fit(x)
            
        # do this so the UI can pick up that the estimate changed
        self._som = soms                    
         
    def apply(self, experiment):
        """
        Apply the self-organizing maps clustering to the data.
        
        Returns
        -------
        Experiment
            a new Experiment with one additional entry in `Experiment.conditions` 
            named `name`, of type ``category``.  The new category has 
            values  ``name_1``, ``name_2``, etc to indicate which k-means cluster 
            an event is a member of.
            
            The new `Experiment` also has one new statistic called
            ``centers``, which is a list of tuples encoding the centroids of each
            k-means cluster.
        """
 
        if experiment is None:
            raise util.CytoflowOpError('experiment',
                                       "No experiment specified")
         
        # make sure name got set!
        if not self.name:
            raise util.CytoflowOpError('name',
                                       "You have to set the gate's name "
                                       "before applying it!")
            
        if self.name != util.sanitize_identifier(self.name):
            raise util.CytoflowOpError('name',
                                       "Name can only contain letters, numbers and underscores."
                                       .format(self.name)) 
         
        if self.name in experiment.data.columns:
            raise util.CytoflowOpError('name',
                                       "Experiment already has a column named {0}"
                                       .format(self.name))
            
        if not self._som:
            raise util.CytoflowOpError(None, 
                                       "No components found.  Did you forget to "
                                       "call estimate()?")
         
        if len(self.channels) == 0:
            raise util.CytoflowOpError('channels',
                                       "Must set at least one channel")
 
        for c in self.channels:
            if c not in experiment.data:
                raise util.CytoflowOpError('channels',
                                           "Channel {0} not found in the experiment"
                                      .format(c))
                 
        for c in self.scale:
            if c not in self.channels:
                raise util.CytoflowOpError('scale',
                                           "Scale set for channel {0}, but it isn't "
                                           "in the experiment"
                                           .format(c))
        
        for b in self.by:
            if b not in experiment.data:
                raise util.CytoflowOpError('by',
                                           "Aggregation metadata {} not found, "
                                           "must be one of {}"
                                           .format(b, experiment.conditions))
        
                 
        if self.by:
            groupby = experiment.data.groupby(self.by, observed = True)
        else:
            # use a lambda expression to return a group that contains
            # all the events
            groupby = experiment.data.groupby(lambda _: True, observed = True)
                 
        event_assignments = pd.Series(["{}_None".format(self.name)] * len(experiment), dtype = "object")
                     
        for group, data_subset in groupby:
            if len(data_subset) == 0:
                raise util.CytoflowOpError('by',
                                           "Group {} had no data"
                                           .format(group))
            
            if group not in self._som:
                raise util.CytoflowOpError('by',
                                           "Group {} not found in the estimated model. "
                                           "Do you need to re-run estimate()?"
                                           .format(group))    
            
            x = data_subset.loc[:, self.channels[:]]
            for c in self.channels:
                x[c] = self._scale[c](x[c])
                 
            # which values are missing?
 
            x_na = pd.Series([False] * len(x))
            for c in self.channels:
                x_na[np.isnan(x[c]).values] = True
                         
            x = x.values
            x_na = x_na.values
            group_idx = data_subset.index
            
            som = self._som[group]
  
            predicted = np.full(len(x), -1, "int")
            predicted[~x_na] = som.predict(x[~x_na])
                 
            predicted_str = pd.Series(["(none)"] * len(predicted))
            for c in np.unique(predicted):
                predicted_str[predicted == c] = "{0}_{1}".format(self.name, c + 1)
            predicted_str[predicted == -1] = "{0}_None".format(self.name)
            predicted_str.index = group_idx
      
            event_assignments.iloc[group_idx] = predicted_str
         
        new_experiment = experiment.clone(deep = False)          
        new_experiment.add_condition(self.name, "category", event_assignments)
        
        # TODO - add a statistic with the proportion of events in each cluster
         
        new_experiment.history.append(self.clone_traits(transient = lambda _: True))
        return new_experiment
    

    def default_view(self, **kwargs):
        """
        Returns a diagnostic plot of the self-organized maps clustering.
         
        Returns
        -------
            IView : an IView, call `SOM1DView.plot` to see the diagnostic plot.
        """
        pass
