"""
Test suite for the navigation.utils.gmt module
"""
import os
import doctest
import unittest
from rockfish2.navigation.utils import gmt


class gmtTestCase(unittest.TestCase):
    """
    Tests for the navigation.utils.gmt module
    """
    # Tests covered by doctests, so far
    pass


def suite():
    testSuite = unittest.makeSuite(gmtTestCase, 'test')
    testSuite.addTest(doctest.DocTestSuite(gmt))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
