"""
Test suite for navigation.cartesian module 
"""
import os
import doctest
import unittest
import numpy as np
from rockfish2.navigation.utils import cartesian


class cartesianTestCase(unittest.TestCase):
    """
    Tests for the navigation.cartesian module 
    """
    def test_cumdist(self):
        """
        Should calculate distance along a line
        """
        # should calculate cumlative distance
        x = [0, 1, 2, 3, 4, 5]
        y = [0, 0, 0, 0, 0, 0]

        r0 = np.cumsum(np.diff(x))
        r1 = cartesian.cumdist(x, y)
        
        for x0, x1 in zip(r0, r1[1:]):
            self.assertEqual(x0, x1)
        
        # first element should be zero (at start of line)
        self.assertEqual(r1[0], 0.0)

        # verify calculation for realistic line
        x0, y0 = (61475.9, 3601321.9)
        r0 = 12.5 * np.arange(468)

        az = 36.2
        x = x0 + r0 * np.cos(np.deg2rad(az))
        y = y0 + r0 * np.sin(np.deg2rad(az))

        r1 = cartesian.cumdist(x, y)
        for _r0, _r1 in zip(r0, r1):
            self.assertAlmostEqual(_r0, _r1, 6)

        # should raise AssertionError if x, y not same size
        self.assertRaises(AssertionError, cartesian.cumdist, [0], [1, 2])

    def test_distribute(self):
        """
        Should distribute points along a line
        """
        x = np.linspace(30000., 35000., 100.)
        y = x

        # should return equal coordinates when azimuth = 45
        length = cartesian.cumdist(x, y)[-1]
        offsets = np.linspace(0, length, 100)
        x1, y1 = cartesian.distribute(x, y, offsets)
        for _x1, _y1 in zip(x1, y1):
            self.assertEqual(_x1, _y1)

        # should return a point for each offset
        self.assertEqual(len(x1), len(offsets))
        self.assertEqual(len(y1), len(offsets))

        # should raise a ValueError if offset is outside of range
        self.assertRaises(ValueError, cartesian.distribute, x, y, [1e9])
        self.assertRaises(ValueError, cartesian.distribute, x, y, [-1e9])



def suite():
    testSuite = unittest.makeSuite(cartesianTestCase, 'test')
    testSuite.addTest(doctest.DocTestSuite(cartesian)) # include doctests

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
