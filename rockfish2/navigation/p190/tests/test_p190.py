"""
Test suite for the p190.P190 module
"""
import os
import doctest
import unittest
from rockfish2.utils.loaders import get_example_file
from rockfish2.navigation.p190 import p190
from rockfish2.navigation.p190.p190 import P190

#XXX dev
from rockfish2.navigation.p190.database import P190Database


class p190TestCase(unittest.TestCase):

    def test_init(self):
        """
        Should initialize a new P190 instance
        """
        p190 = P190()

        # should have default tables
        for table in [p190.HDR_TABLE, p190.COORD_TABLE, p190.REC_PT_TABLE]:
            self.assertTrue(table in p190.tables)
    
    def test_init_disk(self):
        """
        Should create a new database on the disk
        """
        dbfile = 'temp.test_init_disk.sqlite'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        p190 = P190(database=dbfile)

        self.assertTrue(os.path.isfile(dbfile))

        os.remove(dbfile)

    def test_read_p190_disk(self):
        """
        Should read data from file to database on disk 
        """
        dbfile = 'temp.test_read_p190.sqlite'
        if os.path.isfile(dbfile):
            os.remove(dbfile)

        p190 = P190(database=dbfile, input_srid=32419)

        filename = get_example_file('MGL1407MCS15.TEST.p190')
        p190.read_p190(filename)

        os.remove(dbfile)


def suite():
    testSuite = unittest.makeSuite(p190TestCase, 'test')
    testSuite.addTest(doctest.DocTestSuite(p190))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

