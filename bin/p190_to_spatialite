#!/usr/bin/env python
"""
Load UKOAA P1/90 format data into a Spatialite database
"""
import os
import argparse
from rockfish2.navigation.ukooa.p190.p190 import P190

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('p190_file', type=str, help='P190-format input file')
    parser.add_argument('p190_srid', type=int, help='EPSG projection ID')
    parser.add_argument('dbfile', type=str, help='Spatialite database file')
    parser.add_argument('--overwrite', default=False,
            action='store_true', help='Overwrite existing database file')
    args = parser.parse_args()


    if os.path.isfile(args.dbfile):
        if args.overwrite:
            os.remove(args.dbfile)
        else:
            raise IOError('Output file exists: {:}'.format(args.dbfile))

    p190 = P190(database=args.dbfile, input_srid=args.p190_srid)
    p190.read_p190(args.p190_file)
