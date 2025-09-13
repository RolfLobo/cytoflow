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
Created on Feb 4, 2018

@author: brian
'''
import unittest
import cytoflow as flow
import pandas as pd
from .test_base import ImportedDataTest

class TestKMeans(ImportedDataTest):

    def setUp(self):
        ImportedDataTest.setUp(self)

        self.op = flow.KMeansOp(name = "KM",
                                channels = ["V2-A", "Y2-A"],
                                scale = {"V2-A" : "logicle",
                                         "Y2-A" : "logicle"},
                                num_clusters = 2)
        
    def testEstimate(self):
        self.op.estimate(self.ex)
        ex2 = self.op.apply(self.ex)
        self.assertEqual(len(ex2['KM'].unique()), 2)
        
        self.assertIsInstance(ex2.data.index, pd.RangeIndex)
        
    def testEstimate1D(self):
        self.op.channels = ["V2-A"]
        self.op.scale = {"V2-A" : "logicle"}
        self.op.estimate(self.ex)
        ex2 = self.op.apply(self.ex)
        self.assertEqual(len(ex2['KM'].unique()), 2)
        
        self.assertIsInstance(ex2.data.index, pd.RangeIndex)
        
    def testEstimateBy(self):
        self.op.by = ["Well"]
        self.op.estimate(self.ex)
        
        ex2 = self.op.apply(self.ex)
        self.assertEqual(len(ex2['KM'].unique()), 2)

    def testEstimateBy2(self):
        self.op.by = ["Well", "Dox"]
        self.op.estimate(self.ex)
        
        ex2 = self.op.apply(self.ex)
        self.assertEqual(len(ex2['KM'].unique()), 2)
        
    def testPlot(self):
        self.op.estimate(self.ex)
        self.op.default_view().plot(self.ex)

    def testPlot1D(self):
        self.op.channels = ["V2-A"]
        self.op.scale = {"V2-A" : "logicle"}
        self.op.estimate(self.ex)
        self.op.default_view().plot(self.ex)
        
    def testPlotBy1(self):
        self.op.by = ["Dox"]
        self.op.estimate(self.ex)
        self.op.default_view().plot(self.ex, plot_name = 10.0)
        
    def testPlotByIter1(self):
        self.op.by = ["Dox"]
        self.op.estimate(self.ex)
        dv = self.op.default_view()
        for v in dv.enum_plots(self.ex):
            self.op.default_view().plot(self.ex, plot_name = v)
            
    def testPlotBy2(self):
        self.op.by = ["Well", "Dox"]
        self.op.estimate(self.ex)
        self.op.default_view().plot(self.ex, plot_name = ('B', 100.0))
        
    def testPlotByIter2(self):
        self.op.by = ["Well", "Dox"]
        self.op.estimate(self.ex)
        dv = self.op.default_view()
        for v in dv.enum_plots(self.ex):
            self.op.default_view().plot(self.ex, plot_name = v)
        
    def testPlotBySubset(self):
        self.op.by = ["Well", "Dox"]
        self.op.estimate(self.ex)
        self.op.default_view(subset = "Dox == 10.0").plot(self.ex, plot_name = ('A', 10.0))



if __name__ == "__main__":
#     import sys;sys.argv = ['', 'TestKMeans.testEstimateBy1Channel']
    unittest.main()
