"""
Test suite for the cps.model module
"""
import os
import doctest
import unittest
import datetime
import numpy as np
import matplotlib.pyplot as plt
from rockfish2.utils.loaders import get_example_file
from rockfish2.extensions.cps import model

PLOT = True 

class modelTestCase(unittest.TestCase):
    """
    Tests for the cps.model module
    """
    def test_init_empty(self):
        """
        Should initialize a CPSModel instance with an empty model
        """
        m = model.CPSModel1d()

        self.assertEqual(len(m.model), 0)
        self.assertTrue(hasattr(m, 'write_model'))\

    def test_write(self):
        """
        Should write data to a CPS ASCII model format
        """
        m = model.CPSModel1d(index=[0, 500, 1000],
                data=[[1.5,0], [1.6, 0.2], [3, 0.3]],
                columns=['Vp', 'Vs'], index_name='depth')

        modfile = 'temp.mod'
        if os.path.isfile(modfile):
            os.remove(modfile)

        m.write_model(modfile)

        self.assertTrue(os.path.isfile(modfile))

        # TODO verify model contents

        os.remove(modfile)

    def dev__sprep96(self):
        """
        Should run sprep96 for the current model
        """

        m = model.CPSModel1d(index=[0, 0.5, 1.0],
                data=[[1.5,0], [1.6, 0.2], [3, 0.3]],
                columns=['Vp', 'Vs'], index_name='depth')

        m.interp(method='nyquist', inplace=True)

        m._sprep96()



 
def suite():
    testSuite = unittest.makeSuite(modelTestCase, 'dev')
    #XXX testSuite.addTest(doctest.DocTestSuite(database))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

