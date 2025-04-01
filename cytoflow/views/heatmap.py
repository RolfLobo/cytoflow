#!/usr/bin/env python3.11
# coding: latin-1

# (c) Massachusetts Institute of Technology 2015-2018
# (c) Brian Teague 2018-2025
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
cytoflow.views.heatmap
----------------------

A statistics view that plots a heatmap of a statistic. The indices of the 
statistic determine the facets for the heatmap, and the values determine
the color. The size of the heatmap's circles can be fixed, or relative to the
number of events in the faceted groups. Optionally, a second statistic can
be passed with the same index levels, and its values (single numbers or
tuples) are used as centroid locations in a minimum spanning tree.
"""
