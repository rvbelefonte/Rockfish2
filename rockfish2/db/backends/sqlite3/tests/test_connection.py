"""
Tests for the sqlite3.connection module
"""
import os
import doctest
import unittest
from rockfish2.db.backends.sqlite3 import connection


class baseTestCase(unittest.TestCase):

    def test_init_default(self):
        """
        Should create a new Connection to a db in memory
        """
        db = connection.Connection()
        self.assertFalse(os.path.isfile(':memory:'))

    def test_init_file(self):
        """
        Should create a new Connection to a db on the disk
        """
        dbfile = 'temp.db'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        db = connection.Connection(database=dbfile)

        self.assertTrue(os.path.isfile(dbfile))

        os.remove(dbfile)

    def test_init_spatialite(self):
        """
        Should initialize a new spatialite database or raise an error is
        spatialite is not enabled
        """
        db = connection.Connection()

        if connection.SPATIALITE_ENABLED:
            db.init_spatialite()
            self.assertTrue('spatial_ref_sys' in db.tables)

            # should have spatialite tools
            sql = "CREATE TABLE test (fid INTEGER NOT NULL)"
            db.execute(sql)

            sql = """SELECT addGeometryColumn('test', 'geom', 4326,
                'LINESTRING', 'XY')"""
            db.execute(sql)

        else:
            self.assertRaises(db.ConfigurationError, db.init_spatialite)

    def test_tables(self):
        """
        Should return list of tables
        """
        # new db should return empty list
        db = connection.Connection()
        self.assertEqual(len(db.tables), 0)

    def test_views(self):
        """
        Should return list of views
        """
        # new db should return empty list
        db = connection.Connection()
        self.assertEqual(len(db.views), 0)


def suite():
    testSuite = unittest.makeSuite(baseTestCase, 'test')

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
