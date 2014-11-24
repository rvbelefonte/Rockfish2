"""
Test suite for the database.utils module
"""
import os
import doctest
import unittest
from rockfish2.database import utils


class utilsTestCase(unittest.TestCase):
    """
    Tests for the database.utils module
    """
    # Tests covered by doctests, so far
    pass


def suite():
    testSuite = unittest.makeSuite(utilsTestCase, 'test')
    testSuite.addTest(doctest.DocTestSuite(utils))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
