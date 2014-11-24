"""
Test suite for the p190.binning module
"""
import os
import doctest
import unittest
import numpy as np
import time
import matplotlib.pyplot as plt
from rockfish2.utils.loaders import get_example_file
from rockfish2.database.database import DatabaseError,\
    DatabaseIntegrityError, DatabaseOperationalError
from rockfish2.navigation.p190 import binning
from rockfish2.navigation.p190.p190 import P190
from rockfish2.navigation.utils.cartesian import cumdist


class binningTestCase(unittest.TestCase):

    def test__create_bin_line(self):
        """
        Should layout points along a line
        """
        p190 = P190(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        sql = """SELECT X(geom) as x, Y(geom) as y
                FROM p190_coords WHERE record_id='S'"""
        dat = p190.read_sql(sql)

        offset, x, y = p190._create_bin_line(dat['x'], dat['y'], 6.25)

        self.assertAlmostEqual(np.mean(np.diff(cumdist(x, y))), 6.25, 3)

    def test__calc_bin_rectangles(self):
        """
        Should calculate corners of rectangular bins
        """
        p190 = P190(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        sql = """SELECT X(geom) as x, Y(geom) as y
                FROM p190_coords WHERE record_id='S'"""
        dat = p190.read_sql(sql)

        p190.create_bin_line(dat['x'], dat['y'])

        cmps = p190._calc_bin_rectangles(dat['x'], dat['y'], 12.5, 500)

        self.assertEqual(len(cmps), 8)
        self.assertEqual(len(cmps[0]), len(dat))

    def test_create_bin_line(self):
        """
        Should layout points along a line
        """
        p190 = P190(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        sql = """SELECT X(geom) as x, Y(geom) as y
                FROM p190_coords WHERE record_id='S'"""
        dat = p190.read_sql(sql)

        p190.create_bin_line(dat['x'], dat['y'])

        # should have created default table
        self.assertTrue(p190.CMP_MODEL in p190.tables)
        self.assertTrue('bin' in p190._get_fields(p190.CMP_MODEL))
        self.assertTrue('offset' in p190._get_fields(p190.CMP_MODEL))
        self.assertTrue('bin_center' in p190._get_fields(p190.CMP_MODEL))
        
        # should have inserted data
        cmps = p190.read_table(p190.CMP_MODEL)
        self.assertEqual(len(cmps), 409)
        
        # should fail when attempting to overwrite existing model
        self.assertRaises(DatabaseError, p190.create_bin_line, dat['x'],
                dat['y'])
        
        self.assertRaises(DatabaseIntegrityError, p190.create_bin_line,
                dat['x'], dat['y'], if_exists='append')
        
        # should replace model if if_exists=replace
        p190.create_bin_line(dat['x'], dat['y'], if_exists='replace')

    def test_create_bin_line_rect(self):
        """
        Should layout rectangular bins
        """
        p190 = P190(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        sql = """SELECT X(geom) as x, Y(geom) as y
                FROM p190_coords WHERE record_id='S'"""
        dat = p190.read_sql(sql)

        p190.create_bin_line(dat['x'], dat['y'], bin_shape='rect')

        # should have created table and added data
        cmps = p190.read_table(p190.CMP_MODEL)
        self.assertEqual(len(cmps), 409)

        # should have polygon field
        self.assertTrue('bin_geom' in cmps)

        sql = "SELECT AsText(bin_geom) FROM '{:}'".format(p190.CMP_MODEL)
        poly1 = p190.execute(sql).fetchone()[0][9:-2]
        pts1 = [[float(v) for v in _pt.split()] for _pt in poly1.split(',')]

        pts0 = [[63569.380701, 3600203.67845], [63564.290495, 3600207.30506],
                [63854.419299, 3600614.52155], [63859.509505, 3600610.89494]]
        for pt0, pt1 in zip(pts0, pts1):
            self.assertEqual(pt0[0], pt1[0])
            self.assertEqual(pt0[1], pt1[1])

    def test_create_bin_line_from_midpoints(self):
        """
        Should create a bin line from cable midpoints
        """
        p190 = P190(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        # should get coordinates and pass kwargs to create_bin_line()
        p190.create_bin_line_from_midpoints(bin_shape='rect')

        # should have created table and added data
        cmps = p190.read_table(p190.CMP_MODEL)
        self.assertEqual(len(cmps), 400)

        # should have polygon field
        self.assertTrue('bin_geom' in cmps)

    def test_ST_Contains(self):
        """
        Spatialite ST_Contains should determine if points are in polygon
        """
        p190 = P190()

        # table with one polygon 
        sql = """CREATE TABLE test_polys(bin)"""
        p190.execute(sql)
        p190._add_geom_polyxy('test_polys', 'geom')

        sql = """INSERT INTO test_polys(bin, geom) VALUES(
            1000, GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))', -1))"""
        p190.execute(sql)

        # table with points 
        sql = """CREATE TABLE test_pts(point)"""
        p190.execute(sql)
        p190._add_geom_pointxy('test_pts', 'geom')

        pts = [(900, 'POINT(0.5 0.5)'),
               (901, 'POINT(0.4 0.2)'),
               (902, 'POINT(1.5 0.2)'),
               (903, 'POINT(-0.4 0.2)')]

        sql = """INSERT INTO test_pts(point, geom) VALUES(
            ?, GeomFromText(?, -1))"""
        p190.executemany(sql, pts)

        # should count points in polygon
        sql = """SELECT count(p.point)
            FROM test_pts as p, test_polys as b
            WHERE ST_Contains(b.geom, p.geom)"""
        self.assertEqual(p190.execute(sql).fetchone()[0], 2)

        # should only return records where point is in polygon
        sql = """SELECT p.point as point
            FROM test_pts as p, test_polys as b
            WHERE ST_Contains(b.geom, p.geom)"""
        dat = p190.execute(sql).fetchall()
        self.assertEqual(len(dat), 2)

        # should match polygons with points
        sql = """INSERT INTO test_polys(bin, geom) VALUES(
            1001, GeomFromText('POLYGON((1 0, 2 0, 2 1, 1 1, 1 0))', -1))"""
        p190.execute(sql)

        sql = """SELECT p.point as point, b.bin as bin
            FROM test_pts as p, test_polys as b
            WHERE ST_Contains(b.geom, p.geom)"""
        dat = p190.execute(sql).fetchall()

        self.assertEqual(len(dat), 3)
        self.assertEqual(dat[0][1], 1000)
        self.assertEqual(dat[1][1], 1000)
        self.assertEqual(dat[2][1], 1001)

    def dev_assign_cmp_bins(self):
        """
        Should assign points to bins 
        """
        dbfile = 'temp.test_assign_cmp_bins.sqlite'
        
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        p190 = P190(database=dbfile, input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        # create bin line from cable midpoint
        p190.create_bin_line_from_midpoints(spacing=6.25, bin_shape='rect')

        # should build a table of CMP assignments
        drop_sql = "DROP TABLE IF EXISTS {:}".format(p190.CMP_ASSIGNMENTS)
        for spatial_index in [True, False]:
            p190.execute(drop_sql)

            tic = time.clock()
            p190.assign_cmp_bins(spatial_index=spatial_index)
            toc = time.clock()

            print 'Assigned bins in {:} seconds with spatial_index={:}'\
                    .format(toc - tic, spatial_index)

            sql = "SELECT bin, count(bin) FROM '{:}' GROUP BY bin"\
                    .format(p190.CMP_ASSIGNMENTS)
            dat = p190.execute(sql).fetchall()
    
            self.assertEqual(len(dat), 400)
            self.assertEqual(dat[0][1], 27)

        # should have created natural join table back to rec_pt
        self.assertTrue(p190.CMP_ASSIGNMENTS_VIEW in p190.views)
        dat1 = p190.execute("SELECT * FROM '{:}'"\
                .format(p190.CMP_ASSIGNMENTS_VIEW)).fetchall()
        self.assertEqual(p190.count(p190.CMP_ASSIGNMENTS), len(dat1))


        dat = p190.read_table(p190.CMP_ASSIGNMENTS_VIEW)

        os.remove(dbfile)


def suite():
    testSuite = unittest.makeSuite(binningTestCase, 'dev')
    testSuite.addTest(doctest.DocTestSuite(binning))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

