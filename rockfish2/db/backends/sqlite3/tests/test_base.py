"""
Test suite for the sqlite3.base module
"""
import os
import doctest
import unittest
from rockfish2.db.backends.sqlite3 import base


class baseTestCase(unittest.TestCase):

    def test_init(self):
        """
        Base module should have required attributes
        """
        self.assertTrue(hasattr(base, 'dbapi2'))
        self.assertTrue(hasattr(base, 'OperationalError'))
        self.assertTrue(hasattr(base, 'IntegrityError'))

    def test_create_db_memory(self):
        """
        Should create a new database in memory
        """
        db = base.dbapi2.Connection(':memory:')
        self.assertFalse(os.path.isfile(':memory:'))

    def test_create_db_disk(self):
        """
        Should create a new database on the disk
        """
        dbfile = 'temp.db'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        db = base.dbapi2.Connection(dbfile)

        self.assertTrue(os.path.isfile(dbfile))

        os.remove(dbfile)


def suite():
    testSuite = unittest.makeSuite(baseTestCase, 'test')

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
