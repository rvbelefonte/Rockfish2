"""
Test suite for the antelope.database module
"""
import os
import doctest
import unittest
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from logbook import Logger
from obspy import UTCDateTime
from rockfish2.utils.loaders import get_example_file
from rockfish2.extensions.antelope import database
from rockfish2.extensions.obspy import stream

PLOT = False 

logging = Logger(os.path.basename(__file__))

class databaseTestCase(unittest.TestCase):
    """
    Tests for the navigation.p190.io module
    """
    def test_init_empty(self):
        """
        Should initialize an AntelopeDatabase instance
        """
        # calling with no arguments should initialize an empty instance
        sdb = database.AntelopeDatabase()
        self.assertTrue(hasattr(sdb, 'execute'))

    def test_init_read_spatial(self):
        """
        Should initialize a spatial AntelopeDatabase instance and read data
        """
        dbfile = 'temp.sqlite'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'),
                database=dbfile, spatial=True)

        self.assertTrue(os.path.isfile(dbfile))

        tables1 = sdb._get_tables()
        self.assertTrue('wfdisc' in sdb.tables)
        self.assertTrue('_site' in sdb.tables)
        self.assertTrue('site' in sdb.views)
        self.assertTrue('sitechan' in sdb.tables)

        os.remove(dbfile)

    def test_init_read_nonspatial(self):
        """
        Should initialize a non-spatial AntelopeDatabase instance and read data
        """
        dbfile = 'temp.sqlite'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        # default should be non-spatial
        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'),
                database=dbfile)

        self.assertTrue(os.path.isfile(dbfile))

        tables1 = sdb._get_tables()
        self.assertTrue('wfdisc' in sdb.tables)
        self.assertTrue('_site' not in sdb.tables)
        self.assertTrue('site' in sdb.tables)
        self.assertTrue('sitechan' in sdb.tables)

        os.remove(dbfile)

    def test__create_table_site(self):
        """
        Should create the '_site' table and 'site' view
        """
        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'),
                read_tables=False, spatial=True)

        self.assertFalse('_site' in sdb.tables)
        self.assertFalse('site' in sdb.views)

        sdb._create_table_site()
        
        self.assertTrue('_site' in sdb.tables)

        fields = sdb._get_fields('_site')
        for f in ['sta', 'ondate', 'geom']:
            self.assertTrue(f in fields)

    def run__read_table(self, kind='wfdisc'):
        """
        General test for table reading 
        """
        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'),
                read_tables=False)

        txt_path = sdb.PATH + '.' + kind
        dat = sdb._read_table(txt_path, kind)

        # should return a DataFrame
        self.assertTrue(isinstance(dat, pd.DataFrame))
        
        # should have an entry for each row
        num_lines = sum(1 for line in open(txt_path))
        self.assertEqual(len(dat), num_lines)

        # should have all collumns
        fmt = database.TABLE_FORMATS[kind]
        names = [c[0] for c     in fmt]
    
        cols = [k for k in dat]
        for n in names:
            self.assertTrue(n in cols)

        return dat

    def test__read_table_wfdisc(self):
        """
        Should read data from the sitechan table
        """
        dat = self.run__read_table(kind='wfdisc')
        
        self.assertEqual(dat.ix[0]['sta'], 'S07')
        self.assertEqual(dat.ix[0]['chan'], 'EDH')
        self.assertEqual(dat.ix[0]['time'], 1341619185.20000)
        self.assertEqual(dat.ix[0]['wfid'], 1)
        self.assertEqual(dat.ix[0]['chanid'], 7)
        self.assertEqual(dat.ix[0]['jdate'], 2012188)
        self.assertEqual(dat.ix[0]['endtime'], 1341619204.69000) 
        self.assertEqual(dat.ix[0]['nsamp'], 1950)
        self.assertEqual(dat.ix[0]['samprate'], 100.0000000)
        self.assertEqual(dat.ix[0]['calib'], 0)
        self.assertEqual(dat.ix[0]['calper'], -1.)
        self.assertEqual(dat.ix[0]['instype'].strip(), '-')
        self.assertEqual(dat.ix[0]['segtype'].strip(), '-')
        self.assertEqual(dat.ix[0]['datatype'].strip(), 'sd')
        self.assertEqual(dat.ix[0]['clip'].strip(), '-')
        self.assertEqual(dat.ix[0]['dir'].strip(),
                'Deploy_201207/Mseed/D02/Data/2012/188')
        self.assertEqual(dat.ix[0]['dfile'].strip(),
                'XX_3165_EDH__2012_188.msd')
        self.assertEqual(dat.ix[0]['foff'], 0)
        self.assertEqual(dat.ix[0]['commid'], -1)
        self.assertEqual(dat.ix[0]['Iddate'], 1389885015.48085)

    def test__read_table_sitechan(self):
        """
        Should read data from the sitechan table
        """
        dat = self.run__read_table(kind='sitechan')
        
        self.assertEqual(dat.ix[0]['sta'], 'S07')
        self.assertEqual(dat.ix[0]['chan'], 'ELZ')
        self.assertEqual(dat.ix[0]['ondate'], 2012188)
        self.assertEqual(dat.ix[0]['chanid'], 1)
        self.assertEqual(dat.ix[0]['offdate'], 2012342)
        self.assertEqual(dat.ix[0]['ctype'], '-')
        self.assertEqual(dat.ix[0]['edepth'], 0.0000)
        self.assertEqual(dat.ix[0]['hang'], 0.0)
        self.assertEqual(dat.ix[0]['vang'], 0.0)
        self.assertEqual(dat.ix[0]['descrip'].strip(), '14 3165')
        self.assertEqual(dat.ix[0]['Iddate'], 1389559137.26375) 

    def test__read_table_site(self):
        """
        Should read data from the site table
        """
        # parser should read data correctly
        dat = self.run__read_table(kind='site')

        self.assertEqual(dat.ix[0]['sta'], 'S07')
        self.assertEqual(dat.ix[0]['ondate'], 2012188)
        self.assertEqual(dat.ix[0]['offdate'], 2012342)
        self.assertEqual(dat.ix[0]['lat'], 39.8567)
        self.assertEqual(dat.ix[0]['lon'], -70.9572)
        self.assertEqual(dat.ix[0]['elev'], -0.8430)
        self.assertEqual(dat.ix[0]['staname'].strip(), 'WHOI OBS ID D02')
        self.assertEqual(dat.ix[0]['statype'].strip(), '-')
        self.assertEqual(dat.ix[0]['refsta'].strip(), '-')
        self.assertEqual(dat.ix[0]['dnorth'], 0.)
        self.assertEqual(dat.ix[0]['deast'], 0.)
        self.assertEqual(dat.ix[0]['Iddate'], 1389559137.26400)

        # should create a database table and populate it
        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'),
                read_tables=False, spatial=True)

        sdb._read_table_site()
        self.assertTrue('_site' in sdb.tables)
        self.assertTrue('site' in sdb.views)

    def test__format_time_search(self):
        """
        Should build a SQL query to find time segments
        """
        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'),
                read_tables=False)

        sql0 = 'SELECT * FROM wfdisc WHERE '

        # should find all these for the search interval [10., 20.]
        segments1 = [(5., 15.), (15., 25.), (15., 17.), (5., 25.)]
        dat = pd.DataFrame({'time': [s[0] for s in segments1],
                'endtime': [s[1] for s in segments1]})
        dat.to_sql('wfdisc', sdb)

        sql = sdb._format_time_search(starttime=10, endtime=20)

        dat1 = sdb.read_sql(sql0 + sql)
        self.assertEqual(len(dat1), len(segments1))

        # should not find these
        segments2 = [(1., 5.), (25., 30.)]
        dat = pd.DataFrame({'time': [s[0] for s in segments2],
                'endtime': [s[1] for s in segments2]})
        dat.to_sql('wfdisc', sdb, if_exists='append')
        sql = sdb._format_time_search(starttime=10, endtime=20)
        dat1 = sdb.read_sql(sql0 + sql)
        self.assertEqual(len(dat1), len(segments1))


    def test_find_data(self):
        """
        Should find data
        """
        dbfile = 'temp.sqlite'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'),
                database=dbfile)

        starttime = UTCDateTime(2012, 10, 15, 23, 30)
        endtime = UTCDateTime(2012, 10, 16, 3, 0)

        # calling with default paths_only should return DataFrame
        search = {'chan': ['EDH', 'ELZ'], 'sta': 'S06'}
        dat = sdb.find_data(starttime=starttime, endtime=endtime, 
                **search)
        self.assertTrue(isinstance(dat, pd.DataFrame))

        # calling with paths_only=True should return list of paths
        paths = sdb.find_data(starttime=starttime, endtime=endtime, 
                paths_only=True, **search)
        self.assertTrue(isinstance(paths, list)) 
        self.assertEqual(len(paths), len(dat))

        # segments should overlap with period of interest
        t0_0 = (starttime.datetime\
                - datetime.datetime(1970,1,1)).total_seconds()
        t1_0 = (endtime.datetime\
                - datetime.datetime(1970,1,1)).total_seconds()
            
        for ifile in range(len(dat)):
            self.assertTrue(dat.ix[ifile]['chan'] in ['EDH', 'ELZ'])

        if PLOT:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.fill([t0_0, t1_0, t1_0, t0_0, t0_0],
                    [0, 0, len(dat), len(dat), 0])

            for ifile in range(len(dat)):
                t0 = dat.ix[ifile]['time']
                t1 = dat.ix[ifile]['endtime']

                print dat.ix[ifile]['dir'], dat.ix[ifile]['dfile']
                ax.plot([t0, t1], [ifile + 1, ifile + 1])

            plt.xlabel('Epoch time')
            plt.ylabel('File number')
            plt.show()

        os.remove(dbfile)

    def XXX_read_data(self):
        """
        Should read data into an obspy.Stream()
        """
        sdb = database.AntelopeDatabase(path=get_example_file('USGS_EC'))

        starttime = UTCDateTime(2012, 10, 15, 23, 30)
        endtime = UTCDateTime(2012, 10, 16, 3, 0)

        search = {'chan': ['EDH', 'ELZ'], 'sta': 'S06'}
        st = sdb.read_data(starttime=starttime, endtime=endtime, 
                trim=True, **search)

        print st

        # should use rockfish Stream extension
        self.assertTrue(isinstance(st, stream.Stream))


def suite():
    testSuite = unittest.makeSuite(databaseTestCase, 'test')
    #XXX testSuite.addTest(doctest.DocTestSuite(database))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

