"""
Test suite for usign spatialite extensions with the sqlite3.base module
"""
import os
import doctest
import unittest
from rockfish2.db.backends.sqlite3 import base


class spatialiteTestCase(unittest.TestCase):

    def test_spatialite_enabled(self):
        """
        Should set flag for spatialite functionality
        """
        db = base.dbapi2.Connection(':memory:')
        db.enable_load_extension(True)

        db.execute('SELECT load_extension("libspatialite")')


def suite():
    testSuite = unittest.makeSuite(spatialiteTestCase, 'test')

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
