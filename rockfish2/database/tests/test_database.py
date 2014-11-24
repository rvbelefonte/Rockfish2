"""
Test suite for the rockfish2.database module
"""
import os
import doctest
import unittest
import pandas as pd
from rockfish2.database import database


class databaseTestCase(unittest.TestCase):
    """
    Tests for the database.utils module
    """
    def test_init(self):
        """
        Should initialize a database connection
        """
        db = database.Connection()

        for attr in ['execute', 'executemany', 'commit']:
            self.assertTrue(hasattr(db, attr))

        # should not create a file named :memory: for memory flag
        self.assertFalse(os.path.isfile(':memory:'))

    def test__create_table(self):
        """
        Should have shortcut for creating table
        """
        db = database.Connection()
        db._create_table('test', [('field1', 'INTEGER', None, False, False)])
        self.assertTrue('test' in db.tables)

    def test_insert(self):
        """
        Should add data to the database
        """
        db = database.Connection()
        db._create_table('test', [('field1', 'INTEGER', None, False, False)])
        sql = 'INSERT INTO test(field1) VALUES (999)'
        db.execute(sql)
        dat = db.execute('SELECT field1 FROM test').fetchone()
        self.assertEqual(dat[0], 999)
    
    def test_insert_geom(self):
        """
        insert should work with spatialite geometries
        """
        db = database.Connection(spatial=True)

        sql = "CREATE TABLE test_geom (name TEXT)"
        db.execute(sql)

        sql = "SELECT AddGeometryColumn('test_geom', 'geom', -1, 'POINT',"
        sql += " 'XY');"
        db.execute(sql)

        # should work directly with 
        sql = "INSERT INTO test_geom (name, geom)"
        sql += " VALUES ('point1', GeomFromText('POINT(1.01 2.02)', -1))"
        db.execute(sql)

        dat = db.read_sql('SELECT * FROM test_geom')
        self.assertEqual(len(dat), 1)

        # should work directly with executemany
        sql = "INSERT INTO test_geom (name, geom)"
        sql += "VALUES (?, GeomFromText(?, -1))"
        
        dat = [('point2', 'POINT(2 4)'),
                ('point3', 'POINT(1 2)'),
                ('point4', 'POINT(8 9)')] 
        db.executemany(sql, dat)
        dat = db.read_sql('SELECT * FROM test_geom')
        self.assertEqual(len(dat), 4)

        # expected to fail, for now 
        self.assertRaises(database.DatabaseIntegrityError, db.insert,
                'test_geom', **{'name': 'point2', 
                    'geom': "GeomFromText('POINT(1.01 2.02)', -1)"})

    def test_init_spatial(self):
        """
        Should setup a spatialite database
        """
        # default should be not be spatial
        db = database.Connection()
        self.assertFalse('spatial_ref_sys' in db.tables)

        # spatial=True should enable spatialite
        db = database.Connection(spatial=True)
        self.assertTrue('spatial_ref_sys' in db.tables)

    def test_params(self):
        """
        Should setup a parameters table
        """
        # if name is given, should create a SqliteDict table
        dbfile = 'temp.sqlite'
        if os.path.isfile(dbfile):
            os.remove(dbfile)
        db = database.Connection(database=dbfile, params_table='params')

        # should be able to set persistant value of PARAMS
        db.params['foo'] = 989
        db.close()

        db1 = database.Connection(database=dbfile, params_table='params')

        self.assertEqual(db1.params['foo'], 989)

        # attributes should also be accessible as shortcuts
        self.assertEqual(db1.foo, 989)

        # should be able to reset a value in params from the shortcut
        db1.foo = 888
        self.assertEqual(db1.foo, 888)
        self.assertEqual(db1.params['foo'], 888)

        # should be case insenstive
        db1.params['foobar'] = None
        db1.FooBar = 888
        self.assertEqual(db1.foobar, 888)
        self.assertEqual(db1.FooBar, 888)

        # should always be lower case in params table
        self.assertEqual(db1.params['foobar'], 888)

        # should still be able to set an attribute outside of the param
        # table
        db1.willywonka = 'is cool'
        self.assertTrue(hasattr(db1, 'willywonka'))
        self.assertEqual(db1.willywonka, 'is cool')
        self.assertTrue('willywonka' not in db1.params)

        os.remove(dbfile)

    def test_params_memory(self):
        """
        Should not create a file named :memory: if memory flag is set
        """
        if os.path.isfile(':memory:'):
            os.remove(':memory:')

        db = database.Connection(params_table='params')

        self.assertTrue(isinstance(db.params, dict))
        self.assertFalse(os.path.isfile(':memory:'))

    def test_read_table(self):
        """
        Should read data from a table
        """
        db = database.Connection(params_table='params')

        dat = pd.DataFrame({'one': [1, 2], 'two': [3, 4]})

        dat.to_sql('test_table', db)

        dat1 = db.read_table('test_table')

        self.assertEqual(dat1.ix[0]['one'], 1)
        self.assertEqual(dat1.ix[1]['two'], 4)

    def dev__get_primary_fields(self):
        """
        Should return primary fields
        """
        db = database.Connection()
        sql = """CREATE TABLE test_table(
            point INTEGER NOT NULL,
            chan INTEGER NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY (chan, point))"""

        db.execute(sql)

        pkey1 = db._get_primary_fields('test_table')
        pkey0 = ['chan', 'point']

        for f0, f1 in zip(pkey0, pkey1):
            self.assertEqual(f0, f1)

def suite():
    testSuite = unittest.makeSuite(databaseTestCase, 'test')
    testSuite.addTest(doctest.DocTestSuite(database))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
