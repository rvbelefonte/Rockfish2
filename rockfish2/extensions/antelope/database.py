"""
Tools for interfacing with an Antelope database
"""
import os
import datetime
import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy.core.stream import _read
from rockfish2 import logging
from rockfish2.database.utils import format_where
from rockfish2.db import Connection
from rockfish2.extensions.obspy.stream import Stream

TABLE_FORMATS = {
    'wfdisc': [('sta', (0, 6)), ('chan', (6, 15)), ('time', (15, 33)),
        ('wfid', (33, 43)), ('chanid', (43, 52)), ('jdate', (52, 61)),
        ('endtime', (61, 79)), ('nsamp', (79, 88)), ('samprate', (88, 100)),
        ('calib', (100, 117)), ('calper', (117, 134)),
        ('instype', (134, 141)), ('segtype', (141, 143)),
        ('datatype', (143, 146)), ('clip', (146, 148)),
        ('dir', (148, 213)), ('dfile', (213, 246)),
        ('foff', (248, 257)), ('commid', (257, 267)),
        ('Iddate', (267, 287))],
    'site': [('sta', (0, 6)), ('ondate', (7, 15)), ('offdate', (16, 24)),
        ('lat', (25, 36)), ('lon', (36, 47)), ('elev', (47, 54)),
        ('staname', (54, 106)), ('statype', (106, 110)),
        ('refsta', (110, 114)), ('dnorth', (120, 131)),
        ('deast', (131, 139)), ('Iddate', (139, 161))],
    'sitechan': [('sta', (0, 6)), ('chan', (7, 16)), ('ondate', (16, 24)),
        ('chanid', (25, 33)), ('offdate', (34, 42)), ('ctype', (43, 47)),
        ('edepth', (48, 57)), ('hang', (58, 64)), ('vang', (65, 71)),
        ('descrip', (72, 122)), ('Iddate', (123, 142))]}

iddate2timestamp = lambda t: (datetime.datetime(year=1970, day=1, month=1)\
        + datetime.timedelta(seconds=t)).strftime('%Y-%m-%dT%H:%M:%S.%f')


class AntelopeDatabase(Connection):

    def __init__(self, path=None, database=':memory:', read_tables=True,
            replace=False, spatial=False, srid=4326):
        """
        Interface to an Antelope seismic database

        Parameters
        ----------
        path: str or None, optional
            Root path where the database resides. If `None` (default), an
            empty database is created.
        database: str or ':memory:', optional
            Path to the underlying SQLite database. If ':memory:'
            (default), the SQLite database is created in memory.
        spatial: bool, optional
            Determines whether or not to build a SpatialLite database
            (True) or a standard SQLite database (Fale, default) as the
            underlying database. Setting `spatial=True` requires that the
            SQLite module (:mod:`pysqlite2.dbapi2` or :mod:`sqlite3.dbapi2`)
            can load the Spatiallite extensions.

        Other Parameters
        ----------------
        read_tables:
            Determines whether or not read data from the Antelope tables.
            Default is True (the tables are read).
        replace: bool, optional
            Determines whether or not to replace existing database tables
            before reloading the Antelope tables. Default is not to replace
            data.
        srid: int, optional
            Sets spatial reference ID.  Default is `4326` (WGS84
            geographic). Only used when `spatial=True`.
        """
        Connection.__init__(self, database=database, spatial=spatial)

        self.PATH = path
        self.SRID = srid

        if (self.PATH is not None) and read_tables:
            logging.info('Reading database tables from: {:}',
                    self.PATH)
            self._read_tables(path=self.PATH, replace=replace)

    def _get_spatial(self):
        
        if 'spatial_ref_sys' in self.tables:
            return True
        else:
            return False

    is_spatial = property(fget=_get_spatial)

    def _create_table_site(self, replace=False):

        if self.is_spatial:
            table = '_site'
        else:
            table = 'site'

        if (table in self.tables) and replace:
            self.execute("DROP TABLE {:}".format(table))

        sql = """CREATE TABLE IF NOT EXISTS {:}(
            sta TEXT NOT NULL,
            ondate INTEGER NOT NULL,
            offdate INTEGER NOT NULL,""".format(table)

        if not self.is_spatial:
            sql += "lon REAL, lat REAL, elev REAL,"

        sql += """staname TEXT,
            statype TEXT,
            refsta TEXT,
            Iddate TIMESTAMP CURRENT_TIMESTAMP,
            PRIMARY KEY(sta, ondate))"""  
        #TODO foriegn key on sitechan.sta/chan/ondate

        self.execute(sql)

        if self.is_spatial and ('geom' not in self._get_fields('_site')):
            sql = """SELECT AddGeometryColumn('_site', 'geom', {:},
                'POINT', 'XYZ')""".format(self.SRID)
            self.execute(sql)

    def _create_view_array(self, replace=False):
        """
        Create a view to array geometry
        """
        if ('array' in self.views) and replace:
            self.execute("DROP VIEW array")

        sql = """CREATE VIEW IF NOT EXISTS array AS SELECT
            a.sta AS sta, a.geom AS sta_geom, b.sta AS refsta,
            b.geom AS refsta_geom FROM _site AS a INNER JOIN _site
            AS b ON a.refsta = b.sta"""
        self.execute(sql)

    def _create_view_site(self, replace=False):
        """
        Create a standard, human-readable view to the site table
        """
        assert self.is_spatial,\
                '_create_view_site() requires that database is spatial'

        if ('site' in self.views) and replace:
            self.execute("DROP VIEW site")

        sql = """CREATE VIEW IF NOT EXISTS site AS SELECT
            a.sta AS sta, a.ondate AS ondate, a.offdate AS offdate,
            Y(a.geom) AS lat, X(a.geom) AS lon, Z(a.geom)/1000. AS elev,
            a.staname AS staname, a.statype AS statype,
            a.refsta AS refsta, IFNULL(Distance(CastToXY(b.geom), 
            CastToXY(a.geom)), 0.0) AS dist_m, a.Iddate AS Iddate
            FROM _site AS a INNER JOIN _site AS b ON a.refsta = b.sta"""
        self.execute(sql)

    def _read_tables(self, replace=True, tables=['wfdisc', 'site',
        'sitechan'], **kwargs):
        """
        Read database tables
        """
        path = kwargs.pop('path', self.PATH)

        if replace:
            if_exists = 'replace'
        else:
            if_exists = 'fail'

        for table in tables:

            if table == 'site':
                self._read_table_site(replace=replace)
            else:
                dat = self._read_table('{:}.{:}'.format(path, table), table)
                dat.to_sql(table, self, if_exists=if_exists)

    def _read_table(self, path, kind):

        logging.info('Reading {:} data from: {:}',
                kind, path)

        fmt = TABLE_FORMATS[kind]

        names = [c[0] for c in fmt]
        colspecs = [c[1] for c in fmt]

        dat = pd.read_fwf(path, colspecs=colspecs, names=names,
                header=None, index=False)

        return dat

    def _read_table_site(self, replace=False, **kwargs):

        self._create_table_site(replace=replace)
        
        path = kwargs.pop('path', self.PATH + '.site')
        
        d = self._read_table(path, 'site')

        if self.is_spatial:
            self._create_view_site(replace=replace)

            dat = [[d.loc[i, 'sta'], d.loc[i, 'ondate'], d.loc[i, 'offdate'],
                d.loc[i, 'staname'], d.loc[i, 'statype'],
                d.loc[i, 'refsta'], iddate2timestamp(d.loc[i, 'Iddate']),
                'POINTZ({:} {:} {:})'.format(d.loc[i, 'lon'], d.loc[i, 'lat'],
                    d.loc[i, 'elev'] * 1000.)] for i in range(len(d))]

            dat = np.asarray(dat)

            sql = """INSERT INTO _site(sta, ondate, offdate, staname,
                statype, refsta, Iddate, geom) VALUES(?, ?, ?, ?, ?, ?, ?,
                GeomFromText(?, {:}))""".format(self.SRID)

            self.executemany(sql, dat)

            sql = """UPDATE _site SET refsta=sta WHERE
                (refsta='-' OR refsta IS NULL)"""
            self.execute(sql)

        else:
            dat = [[d.loc[i, 'sta'], d.loc[i, 'ondate'], d.loc[i, 'offdate'],
                d.loc[i, 'lon'], d.loc[i, 'lat'],
                d.loc[i, 'elev'], d.loc[i, 'staname'], d.loc[i, 'statype'],
                d.loc[i, 'refsta'], iddate2timestamp(d.loc[i, 'Iddate'])]\
                        for i in range(len(d))]

            dat = np.asarray(dat)

            sql = """INSERT INTO site(sta, ondate, offdate, lon, lat, elev,
                staname, statype, refsta, Iddate) 
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        
            self.executemany(sql, dat)
            
            sql = """UPDATE site SET refsta=sta WHERE
                (refsta='-' OR refsta IS NULL)"""
            self.execute(sql)

        self.commit()

    def _format_time_search(self, starttime=None, endtime=None):
        """
        Builds SQL for searching for time segments
        """
        # build time range query
        if starttime is None:
            t0 = self.execute('SELECT min(time) FROM wfdisc').fetchone()[0]
        else:
            t0 = starttime
        if endtime is None: 
            t1 = self.execute('SELECT max(endtime) FROM wfdisc').fetchone()[0]
        else:
            t1 = endtime 


        search_fmt = lambda op0, op1, op2, op3, t0, t1:\
                '((time{:}{:}) AND (time{:}{:}) AND'\
                    .format(op0, t0, op1, t1)\
                + '(endtime{:}{:}) AND (endtime{:}{:}))'\
                    .format(op2, t0, op3, t1)

        where = []
        where += [search_fmt('<=', '<=', '>=', '<=', t0, t1)]
        where += [search_fmt('>=', '<=', '>=', '>=', t0, t1)]
        where += [search_fmt('>=', '<=', '>=', '<=', t0, t1)]
        where += [search_fmt('<=', '<=', '>=', '>=', t0, t1)]

        return '(' + ' OR '.join(where) + ')'

    def find_data(self, starttime=None, endtime=None, paths_only=False,
            sort=True, **kwargs):
        """
        Find paths to waveform data in the database

        Parameters
        ----------
        starttime: :class:`obspy.core.utcdatetime.UTCDateTime`, optional
            Specifies the start time of data to find.
        endtime: :class:`obspy.core.utcdatetime.UTCDateTime`, optional
            Specifies the end time of data to find.
        sort: bool, optional
            Determines whether or not to sort paths by time.
        **kwargs:
            Keyword arguments with additional search criteria (e.g.,
            chan='ELZ' or chan=['EDH', 'ELZ']).
        
        Returns
        -------
        data: :class:`pandas.DataFrame` or list
            wfdisc table records (paths_only=False, Default) or list of full
            paths to waveform files (paths_only=True) in the database
        """
        sql = 'SELECT * FROM wfdisc'

        fields = [k for k in self._get_fields('wfdisc')]

        if starttime is not None:
            t0 = (starttime.datetime\
                    - datetime.datetime(1970,1,1)).total_seconds()
        else:
            t0 = None
        
        if endtime is not None:
            t1 = (endtime.datetime\
                    - datetime.datetime(1970,1,1)).total_seconds()
        else:
            t1 = None

        wheres = [self._format_time_search(starttime=t0, endtime=t1)]
        if len(kwargs) > 0:
            _wheres = [format_where(kwargs, valid_fields=fields)]
            wheres += [w for w in _wheres if len(w) > 0]

        if len(wheres) > 0:
            sql += ' WHERE ' + ' AND '.join(wheres)
        
        if sort:
            sql += ' ORDER BY time'

        dat = self.read_sql(sql)

        if paths_only:
            paths = [os.path.join(os.path.dirname(self.PATH), 
                str(dat.ix[i]['dir']),str(dat.ix[i]['dfile'])) for i in 
                range(len(dat))]
            return paths
        else:
            return dat

    def read_data(self, paths=None, starttime=None, endtime=None,
            headonly=False, trim=True, pad=True, nearest_sample=True,
            fill_value=0, merge=False, **kwargs):
        """
        Read waveform data from the database

        Parameters
        ----------
        paths: list, optional
            Gives a list of paths to read data for. Default is to search
            the `wfdisc` table in the database using `starttime`, `endtime`,
            and any other field=value criteria given by `kwargs`.
        starttime: :class:`obspy.core.utcdatetime.UTCDateTime`, optional
            Specifies the start time to read.
        endtime: :class:`obspy.core.utcdatetime.UTCDateTime`, optional
            Specifies the end time to read.
        trim: bool, optional
            Only applied if `starttime` or `endtime` is given. Cuts all traces
            to given start and end time. Default is `True`.
        merge: bool, optional
            Merges traces with same IDs. Default is `True`.
        pad: bool, optional
            Gives the possibility to trim at time points outside the
            time frame of the original trace, filling the trace with the
            given ``fill_value``. Defaults to ``True``.
        nearest_sample: bool, optional
            If set to ``True``, the closest sample is
            selected, if set to ``False``, the next sample containing the time
            is selected. Default is ``True``.
        fill_value: {int, float, ``None``}, optional
            Fill value for gaps. Defaults to `0`. Traces
            will be converted to NumPy masked arrays if no value is given and
            gaps are present.
        **kwargs:
            Keyword arguments with additional search criteria (e.g.,
            chan='ELZ' or chan=['EDH', 'ELZ']).

        Returns
        -------
        stream: :class:`obspy.core.stream.Stream`
            Data stream
        """
        kwargs['starttime'] = starttime
        kwargs['endtime'] = endtime
        kwargs['nearest_sample'] = nearest_sample
        if paths is None:
            paths = self.find_data(paths_only=True, **kwargs)
       
        logging.info('Reading data from {:} files...', len(paths))
        st = Stream()
        for path in paths:
            logging.debug('...{:}',path)

            try:
                st.extend(_read(path, 'MSEED', headonly, **kwargs).traces)
            except IOError as e:
                logging.warn(e.message)

        if merge:
            st = st.merge(fill_value=fill_value)

        if trim and ((starttime is not None) or (endtime is not None)):
            st = st.trim(starttime=starttime, endtime=endtime, pad=pad,
                    nearest_sample=nearest_sample, fill_value=fill_value)

        return st

    def verify_paths(self, **kwargs):
        """
        Verify that data exist at paths given in the wfdisc table

        Parameters
        ----------
        **kwargs:
            Keyword arguments with search criteria (e.g.,
            chan='ELZ' or chan=['EDH', 'ELZ']) for paths to verify

        Returns
        -------
        missing_paths: list
            List of paths that are missing
        """
        missing = []
        for path in self.find_data(paths_only=True, **kwargs):
            if not os.path.isfile(path):
                print "Missing file: {:}".format(path)
                missing.append(path)

        return missing

    def set_refsta(self, value):
        """
        Sets the reference station for all stations

        Parameters
        ----------
        value: str
            Name of the reference station
        """
        if self.is_spatial:
            table = '_site'
        else:
            table = 'site'

        sql = "UPDATE {:} SET refsta='{:}'".format(table, value)
        self.execute(sql)
        self.commit()
