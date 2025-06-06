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
cytoflowgui.workflow.operations.tsne
------------------------------------

"""

import logging

from traits.api import (HasTraits, provides, Str, Property, observe, 
                        List, Dict, Any, Enum)

from cytoflow.operations.tsne import tSNEOp
import cytoflow.utility as util
from ...utility import CallbackHandler

from ..serialization import camel_registry, cytoflow_class_repr, traits_repr, dedent
from ..subset import ISubset

from .operation_base import IWorkflowOperation, WorkflowOperation

tSNEOp.__repr__ = cytoflow_class_repr


class Channel(HasTraits):
    channel = Str
    scale = util.ScaleEnum
    
    def __repr__(self):
        return traits_repr(self)
    
    
@provides(IWorkflowOperation)    
class tSNEWorkflowOp(WorkflowOperation, tSNEOp):
    # use a list of _Channel instead of separate lists/dicts of channels/scales
    channels_list = List(Channel, estimate = True)
    channels = Property(List(Str), 
                        observe = '[channels_list.items,channels_list.items.channel,channels_list.items.scale]')
    scale = Property(Dict(Str, util.ScaleEnum),
                     observe = '[channels_list.items,channels_list.items.channel,channels_list.items.scale]')
    
    # add 'estimate', 'apply' metadata
    name = Str(apply = True)
    by = List(Str, estimate = True)
    perplexity = util.PositiveFloat(10, estimate = True)
    sample = util.UnitFloat(0.01, estimate = True)
    metric = Enum("euclidean", "cosine", "manhattan", "hamming", "dot", "l1", "l2", "taxicab", estimate = True)
    status = Str(status = True)
    
    # add the 'estimate_result' metadata
    _tsne = Dict(Any, Any, estimate_result = True, transient = True)
    
    # override the base class's "subset" with one that is dynamically generated /
    # updated from subset_list
    subset = Property(Str, observe = "subset_list.items.str")
    subset_list = List(ISubset, estimate = True)
    
    # bits for channels
    @observe('[channels_list:items,channels_list:items.channel,channels_list:items.scale]')
    def _channels_updated(self, event):
        self.changed = 'channels_list'
        
    def _get_channels(self):
        return [c.channel for c in self.channels_list]
    
    def _get_scale(self):
        return {c.channel : c.scale for c in self.channels_list}
    
    # bits to support the subset editor
    @observe('subset_list:items.str')
    def _on_subset_changed(self, _):
        self.changed = 'subset_list'
        
    # MAGIC - returns the value of the "subset" Property, above
    def _get_subset(self):
        return " and ".join([subset.str for subset in self.subset_list if subset.str])
    
    def estimate(self, experiment):
        for i, channel_i in enumerate(self.channels_list):
            for j, channel_j in enumerate(self.channels_list):
                if channel_i.channel == channel_j.channel and i != j:
                    raise util.CytoflowOpError("Channel {0} is included more than once"
                                               .format(channel_i.channel))
        
        gui_handler = CallbackHandler(lambda rec, op = self: op.trait_set(status = rec.getMessage()))
        gui_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(gui_handler)
        try:
            super().estimate(experiment, subset = self.subset)
        finally:
            logging.getLogger().removeHandler(gui_handler)
        
    def apply(self, experiment):
        if not self._tsne:
            raise util.CytoflowOpError(None, 'Click "Estimate"!')
        
        gui_handler = CallbackHandler(lambda rec, op = self: op.trait_set(status = rec.getMessage()))
        gui_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(gui_handler)
        try:
            ex = super().apply(experiment)
        finally:
            logging.getLogger().removeHandler(gui_handler)
        
        return ex
    
        
    def clear_estimate(self):
        self._tsne = {}
        self._scale = {}
    
    def get_notebook_code(self, idx):
        op = tSNEOp()
        op.copy_traits(self, op.copyable_trait_names())

        return dedent("""
        op_{idx} = {repr}
        
        op_{idx}.estimate(ex_{prev_idx}{subset})
        ex_{idx} = op_{idx}.apply(ex_{prev_idx})
        """
        .format(repr = repr(op),
                idx = idx,
                prev_idx = idx - 1,
                subset = ", subset = " + repr(self.subset) if self.subset else ""))
        

### Serialization
@camel_registry.dumper(tSNEWorkflowOp, 'tsne', version = 1)
def _dump(op):
    return dict(name = op.name,
                channels_list = op.channels_list,
                perplexity = op.perplexity,
                sample = op.sample,
                metric = op.metric,
                by = op.by,
                subset_list = op.subset_list)
    
@camel_registry.loader('tsne', version = 1)
def _load(data, version):
    return tSNEWorkflowOp(**data)

@camel_registry.dumper(Channel, 'tsne-channel', version = 1)
def _dump_channel(channel):
    return dict(channel = channel.channel,
                scale = channel.scale)
    
@camel_registry.loader('tsne-channel', version = 1)
def _load_channel(data, version):
    return Channel(**data)
