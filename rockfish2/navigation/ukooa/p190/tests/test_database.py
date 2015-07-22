"""
Test suite for the ukooa.p190.database module
"""
import os
import doctest
import unittest
from rockfish2.utils.loaders import get_example_file
from rockfish2.database.database import DatabaseOperationalError,\
        DatabaseIntegrityError
from rockfish2.navigation.ukooa.p190 import database

P190_FILES = [#(filename, nhdr, ncoord, nrec)
        ('MGL1407MCS15.TEST.p190', 39, 156, 24336)]


class databaseTestCase(unittest.TestCase):

    def test_init(self):
        """
        Should initialize a new P190Database instance
        """
        p190 = database.P190Database()

        # should have default tables
        for table in [p190.HDR_TABLE, p190.COORD_TABLE, p190.REC_PT_TABLE]:
            self.assertTrue(table in p190.tables)

    def test__create_table_hdr(self):
        """
        Shoud create header table
        """
        p190 = database.P190Database()

        p190._create_table_hdr()
        self.assertTrue(p190.HDR_TABLE in p190.tables)

        p190.HDR_TABLE = 'foobar'
        p190._create_table_hdr()
        self.assertTrue('foobar' in p190.tables)

    def test__create_table_coord_id(self):
        """
        Should create coordinate id table and populate it
        """
        p190 = database.P190Database()

        # should create table
        p190._create_table_coord_id()
        self.assertTrue(p190.COORD_ID_TABLE in p190.tables)

        # should be populated
        for cid in database.COORD_IDS:
            sql = "SELECT COUNT(record_id) FROM {:} WHERE record_id='{:}'"\
                    .format(p190.COORD_ID_TABLE, cid[0])
            self.assertEqual(p190.execute(sql).fetchone()[0], 1)

    def test__create_table_coord(self):
        """
        Should create coordinate table
        """
        p190 = database.P190Database()

        # should create table
        p190._create_table_coord()
        self.assertTrue(p190.COORD_TABLE in p190.tables)

        # should have foreign key constraint on record_id
        sql = """INSERT INTO '{:}'(line, point, record_id, vessel_id,
            source_id, day_of_year, time) VALUES('MCS01', 9001,
            'XXX', 1, 1, 244, 10023)""".format(p190.COORD_TABLE)
        self.assertRaises(DatabaseIntegrityError, p190.execute, sql)

        # should have a geom column
        self.assertTrue('geom' in p190._get_fields(p190.COORD_TABLE))

    def test__create_view_point_list(self):
        """
        Should create a view with unique line, point values
        """
        p190 = database.P190Database()
        
        # should create view 
        p190._create_view_point_list()
        self.assertTrue(p190.POINT_LIST_VIEW in p190.views)

    def test__create_table_rec_pt(self):
        """
        Should create groups table
        """
        p190 = database.P190Database()

        # should create table
        p190._create_table_rec_pt()
        self.assertTrue(p190.REC_PT_TABLE in p190.tables)

        # should have a geom column
        self.assertTrue('geom' in p190._get_fields(p190.REC_PT_TABLE))

    def test__create_table_rec_pt(self):
        """
        Should create groups table
        """
        p190 = database.P190Database()

        # should create table
        p190._create_table_rec_pt()
        self.assertTrue(p190.REC_PT_TABLE in p190.tables)

        # should have a geom column
        self.assertTrue('rec_pt' in p190._get_fields(p190.REC_PT_TABLE))

    def test__create_view_rec_line(self):
        """
        Should create a view with lines for each cable geometry
        """
        p190 = database.P190Database(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        p190._create_view_rec_line()

        dat = p190.read_table(p190.REC_LINE_VIEW)

        self.assertTrue(len(dat), 52)

    def test__create_view_src_rec(self):
        """
        Should create a view with source-receiver pairs
        """
        p190 = database.P190Database(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        # should have created view on init
        self.assertTrue(p190.SRC_REC_VIEW in p190.views)

        dat = p190.read_table(p190.SRC_REC_VIEW)
        self.assertEqual(p190.count(p190.REC_PT_TABLE), len(dat))

        # should have dynamic midpoint field
        sql = """SELECT X(src_pt) as sx, Y(src_pt) as sy,
            X(rec_pt) as rx, Y(rec_pt) as ry, X(mid_pt) as mx,
            Y(mid_pt) as my FROM '{:}'""".format(p190.SRC_REC_VIEW)
        dat = p190.execute(sql)

        for d in dat:
            mx1 = d[0] + (d[2] - d[0]) / 2.
            my1 = d[1] + (d[3] - d[1]) / 2.
            
            self.assertEqual(mx1, d[4])
            self.assertEqual(my1, d[5])

    def test_SQL_INSERT_COORD(self):
        """
        Should have SQL generator for inserting coordinates
        """
        p190 = database.P190Database()

        sql = p190.SQL_INSERT_COORD

        nfields = [1 for i in sql if i == '?']

        self.assertEqual(len(nfields),
                len(p190._get_fields(p190.COORD_TABLE)))

        line = 'VMGL1407MCS15   1   91010322722.57N0733831.18W  '
        line += '63520.23600513.05083.6253145210 '
        dat = [p190._parse_coord(line)]

        p190.executemany(sql, dat)

        self.assertEqual(p190.count(p190.COORD_TABLE), len(dat))


    def test_SQL_INSERT_HDR(self):
        """
        Should have SQL generator for inserting headers
        """
        p190 = database.P190Database()

        sql = p190.SQL_INSERT_HDR

        nfields = [1 for i in sql if i == '?']

        self.assertEqual(len(nfields),
                len(p190._get_fields(p190.HDR_TABLE)))


    def test_SQL_INSERT_REC(self):
        """
        Should have SQL generator for inserting receivers
        """
        p190 = database.P190Database()

        sql = p190.SQL_INSERT_REC

        print sql

        nfields = [1 for i in sql if i == '?']

        self.assertEqual(len(nfields),
                len(p190._get_fields(p190.REC_PT_TABLE)))

    def test__parse_hdr(self):
        """
        Should parse a header line
        """
        p190 = database.P190Database()

        line = 'H0100SURVEY AREA                2D Seismic - ECS'
        line += ' ' * (79 - len(line))

        dat0 = ['H', '01', '00', 'SURVEY AREA', '2D Seismic - ECS']
        dat1 = p190._parse_hdr(line)
        for f0, f1 in zip(dat0, dat1):
            self.assertEqual(f0, f1)

        # should have same number of fields as header table
        self.assertEqual(len(dat1), len(p190._get_fields(p190.HDR_TABLE)))

    def test__parse_coord(self):
        """
        Should parse a header line
        """
        p190 = database.P190Database()

        line = 'VMGL1407MCS15   1   91010322722.57N0733831.18W  '
        line += '63520.23600513.05083.6253145210 '

        dat0 = ['MGL1407MCS15', ' 91010', 'V', '1', ' ', ' ', '5083.6',
                '253', '145210', '   ', ' ', 'POINT(  63520.2 3600513.0)']
        dat1 = p190._parse_coord(line)

        for f0, f1 in zip(dat0, dat1):
            self.assertEqual(f0, f1)

    def test__parse_rec(self):
        """
        Should parse a receiver line
        """
        p190 = database.P190Database()

        line = 'R0468  63760.33600252.9    0467  63770.93600246.3    0466'
        line += '  63781.63600239.7    1'

        dat0 = [['0468', '1', '    ', 'POINT(  63760.3 3600252.9)'],
                ['0467', '1', '    ', 'POINT(  63770.9 3600246.3)'],
                ['0466', '1', '    ', 'POINT(  63781.6 3600239.7)']]

        dat1 = p190._parse_rec(line)

        for r0, r1 in zip(dat0, dat1):
            for f0, f1 in zip(r0, r1):
                self.assertEqual(f0, f1)

        # should also work on partial line
        line = 'R0468  63760.33600252.9                                  '
        line += '                      1'
        dat0 = [['0468', '1', '    ', 'POINT(  63760.3 3600252.9)']]
        for r0, r1 in zip(dat0, dat1):
            for f0, f1 in zip(r0, r1):
                self.assertEqual(f0, f1)

    def test_read_p190_memory(self):
        """
        Should read P190 data from file into memory
        """
        for test in P190_FILES:
            # should create database in memory
            p190 = database.P190Database()
            filename = get_example_file(test[0])
            p190.read_p190(filename)

            self.assertFalse(os.path.isfile(':memory:'))

            self.assertEqual(p190.count(p190.HDR_TABLE), test[1])
            self.assertEqual(p190.count(p190.COORD_TABLE), test[2])
            self.assertEqual(p190.count(p190.REC_PT_TABLE), test[3])

    def test_read_p190_disk(self):
        """
        Should read P190 data from file into datavase on the disk  
        """
        dbfile = 'temp_read_p190.sqlite'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        p190 = database.P190Database(database=dbfile)
        self.assertTrue(os.path.isfile(dbfile))

        test = P190_FILES[0]
        filename = get_example_file(test[0])
        p190.read_p190(filename)

        self.assertEqual(p190.count(p190.HDR_TABLE), test[1])
        self.assertEqual(p190.count(p190.COORD_TABLE), test[2])
        self.assertEqual(p190.count(p190.REC_PT_TABLE), test[3])

        os.remove(dbfile)

    def test_create_rec_lines(self):
        """
        Should recast receiver points as lines
        """
        p190 = database.P190Database(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        dat0 = p190.read_table(p190.REC_LINE_VIEW)

        p190.create_rec_lines()

        self.assertTrue(p190.REC_LINE_TABLE in p190.tables)

        dat1 = p190.read_table(p190.REC_LINE_TABLE)

        self.assertEqual(len(dat0), len(dat1))

    def test_calc_src_rec_midpoints(self):
        """
        Should add midpoints to rec point table 
        """
        p190 = database.P190Database(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        dat0 = p190.read_table(p190.REC_PT_TABLE)

        # should create a column for output data
        p190.calc_src_rec_midpoints()
        self.assertTrue('mid_pt' in p190._get_fields(p190.REC_PT_TABLE))

        # should not have changed other fields
        dat1 = p190.read_table(p190.REC_PT_TABLE)
        self.assertEqual(len(dat0), len(dat1))
        fields0 = [k for k in dat0]
        for i in range(5):
            for f in fields0:
                self.assertEqual(dat0.ix[i][f], dat1.ix[i][f])

        # should have copied midpoint calculations from view to table
        sql = """SELECT X(mid_pt), Y(mid_pt) FROM '{:}'
            WHERE rec_pt_rowid<=5""".format(p190.SRC_REC_VIEW)
        dat0 = p190.execute(sql)

        sql = """SELECT X(mid_pt), Y(mid_pt) FROM '{:}'
            WHERE rowid<=5""".format(p190.REC_PT_TABLE)
        dat1 = p190.execute(sql)

        for d0, d1 in zip(dat0, dat1):
            self.assertEqual(d0[0], d1[0])
            self.assertEqual(d0[1], d1[1])

    def XXX__create_drop_spatial_index(self):
        """
        Should (re)build a spatial index
        """
        p190 = database.P190Database(input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        # should build spatial index
        p190._create_spatial_index(p190.REC_PT_TABLE, 'rec_pt')
        
        self.assertTrue('idx_{:}_rec_pt'.format(p190.REC_PT_TABLE) in
                p190.tables)

        # should rebuild spatial index

        sql = "DROP TABLE idx_p190_rec_pts_rec_pt_node"
        p190.execute(sql)
        
        sql = "DROP TABLE idx_p190_rec_pts_rec_pt_parent"
        p190.execute(sql)
        
        sql = "DROP TABLE idx_p190_rec_pts_rec_pt_rowid"
        p190.execute(sql)

        sql = "SELECT DisableSpatialIndex('p190_rec_pts', 'rec_pt')"
        p190.execute(sql)
        
        #sql = "DROP TABLE idx_p190_rec_pts_rec_pt"
        #p190.execute(sql)
        
        print p190.tables

        #p190._create_spatial_index(p190.REC_PT_TABLE, 'rec_pt',
        #        rebuild=True)
        
        #self.assertTrue('idx_{:}_rec_pt'.format(p190.REC_PT_TABLE) in
        #        p190.tables)

        # should drop spatial index
        #p190._drop_spatial_index_if_exists(p190.REC_PT_TABLE, 'rec_pt')
        
        #self.assertTrue('idx_{:}_rec_pt'.format(p190.REC_PT_TABLE) not in
        #        p190.tables)


def suite():
    testSuite = unittest.makeSuite(databaseTestCase, 'test')
    testSuite.addTest(doctest.DocTestSuite(database))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


