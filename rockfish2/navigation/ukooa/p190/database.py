"""
SQLite database tools for working with P190 data
"""
import os
import warnings
from rockfish2 import logging
from rockfish2.db.backends.sqlite3.connection import Connection,\
        DatabaseIntegrityError


COORD_IDS = [#(id, desc)
        ('S', 'Center of Source'),
        ('G', 'Receiver Group'),
        ('Q', 'Bin Center'),
        ('A', 'Antenna Position'),
        ('T', 'Tailbuoy Position'),
        ('C', 'Common Mid Point'),
        ('V', 'Vessel Reference Point'),
        ('E', 'Echo Sounder'),
        ('Z', 'Other, defined in H0800')]


class P190Database(Connection):

    def __init__(self, database=':memory:',
            input_srid=-1, geographic_srid=4326,
            hdr_table='p190_hdrs', coord_table='p190_coords', 
            coord_id_table='p190_coord_ids', 
            point_list_view='p190_point_list', rec_pt_table='p190_rec_pts',
            rec_line_table='p190_rec_lines',
            rec_line_view='p190_rec_lines_view',
            src_line_view='p190_src_lines_view',
            src_rec_view='p190_src_rec_view', **kwargs):

        new = not os.path.isfile(database)

        Connection.__init__(self, database=database, spatial=True)

        #XXX this should be handled by spatial=True
        #self._init_spatiallite()

        self.INPUT_SRID = input_srid
        self.OUTPUT_SRID = kwargs.pop('output_srid', input_srid)
        self.GEOGRAPHIC_SRID = geographic_srid
        self.HDR_TABLE = hdr_table
        self.COORD_TABLE = coord_table
        self.COORD_ID_TABLE = coord_id_table
        self.POINT_LIST_VIEW = point_list_view
        self.REC_PT_TABLE = rec_pt_table
        self.REC_LINE_TABLE = rec_line_table
        self.REC_LINE_VIEW = rec_line_view
        self.SRC_LINE_VIEW = src_line_view
        self.SRC_REC_VIEW = src_rec_view

        if new:
            self._create_tables_views()

    def _init_spatiallite(self):

        #XXX this should be handled by db.backends.sqlite3.connection
        #self.enable_load_extension(True)
        #self.execute('SELECT load_extension("mod_spatialite")')

        if "spatial_ref_sys" not in self.tables:
            self.execute('SELECT InitSpatialMetadata()')

    def _add_geom_pointxy(self, table, name):

        if name in self._get_fields(table):
            return

        sql = """SELECT addGeometryColumn('{table}', '{name}',
            {self.INPUT_SRID}, 'POINT', 'XY')""".format(**locals())
        self.execute(sql)

    def _add_geom_polyxy(self, table, name):

        if name in self._get_fields(table):
            return

        sql = """SELECT addGeometryColumn('{table}', '{name}',
            {self.INPUT_SRID}, 'POLYGON', 'XY')""".format(**locals())
        self.execute(sql)

    def _add_geom_linestringxy(self, table, name):

        if name in self._get_fields(table):
            return

        sql = """SELECT addGeometryColumn('{table}', '{name}',
            {self.INPUT_SRID}, 'LINESTRING', 'XY')""".format(**locals())
        self.execute(sql)

    def _create_spatial_index(self, table, column, rebuild=False):
        """
        Builds an RTree Spatial Index on a geometry column, creating any 
        required trigger required in order to enforce full data coherency
        between the main table and Spatial Index

        Parameters
        ----------
        table: str
            Table name
        column: str
            Name of geometry field to index
        rebuild: bool, optional
            Determines whether or not to force a rebuild the spatial index
        """
        exists = "idx_{:}_{:}".format(table, column) in self.tables
        
        if rebuild and exists:
            logging.info('Removing existing spatial index...')
            self._drop_spatial_index_if_exists(table, column)

        elif exists:
            logging.info('Spatial index exists for: {:}.{:}', table,
                    column)
            return

        logging.info('Creating spatial index for {:}.{:} ...', table,
                column)
        sql = "SELECT CreateSpatialIndex('{:}', '{:}')"\
                .format(table, column)
        self.execute(sql)
        self.commit()

    def _create_tables_views(self):

        self.execute('PRAGMA foreign_keys = ON;')
        self._create_table_hdr()
        self._create_view_surveyyear()
        self._create_table_coord_id()
        self._create_table_coord()
        self._create_view_point_list()
        self._create_table_rec_pt()
        self._create_table_rec_line
        self._create_view_rec_line()
        self._create_view_src_line()
        self._create_view_src_rec()

    def _create_table_coord(self):

        sql = """CREATE TABLE IF NOT EXISTS '{:}' (
            line TEXT NOT NULL,
            point INTEGER NOT NULL,
            day_of_year REAL NOT NULL,
            record_id TEXT NOT NULL,
            vessel_id TEXT NOT NULL,
            source_id TEXT,
            tailbuoy_id TEXT,
            water_depth_or_elev REAL,
            spare TEXT,
            spare2 TEXT,
            PRIMARY KEY (line, point, day_of_year, record_id, vessel_id,
                source_id),
            FOREIGN KEY (record_id) REFERENCES {:}(record_id));
            """.format(self.COORD_TABLE, self.COORD_ID_TABLE)
        self.execute(sql)

        self._add_geom_pointxy(self.COORD_TABLE, 'geom')

    def _create_table_coord_id(self):

        if self.COORD_ID_TABLE in self.tables:
            return

        sql = """CREATE TABLE IF NOT EXISTS '{:}' (
            record_id TEXT NOT NULL,
            desc TEXT NOT NULL,
            PRIMARY KEY (record_id));""".format(self.COORD_ID_TABLE)
        self.execute(sql)

        sql = "INSERT INTO '{:}'(record_id, desc) VALUES (?, ?)"\
                .format(self.COORD_ID_TABLE)

        self.executemany(sql, COORD_IDS)

    def _create_table_hdr(self):

        sql = """CREATE TABLE IF NOT EXISTS '{:}' (
	   record_id TEXT NOT NULL,
	   type_id TEXT NOT NULL,
	   type_modifier TEXT NOT NULL,
	   desc TEXT NOT NULL,
	   value TEXT NOT NULL);""".format(self.HDR_TABLE)
        self.execute(sql)

    def _create_table_rec_pt(self):

        sql = """CREATE TABLE IF NOT EXISTS '{self.REC_PT_TABLE}' (
            line TEXT NOT NULL,
            point INTEGER NOT NULL,
            day_of_year REAL NOT NULL,
            chan INTEGER NOT NULL,
            cable_id INTEGER NOT NULL,
            cable_depth REAL DEFAULT 0.0,
            PRIMARY KEY (line, point, day_of_year, chan, cable_id));
            """.format(**locals())
        self.execute(sql)
        
        self._add_geom_pointxy(self.REC_PT_TABLE, 'rec_pt')

    def _create_view_surveyyear(self):
    
        sql = """CREATE VIEW IF NOT EXISTS _p190_surveyyear AS
            SELECT STRFTIME('%s', DATETIME(SUBSTR(value, 0, 5) || '-01-01'))
            AS surveyyear_epoch FROM '{:}' WHERE type_id='02'
            AND type_modifier='00'""".format(self.HDR_TABLE)
        self.execute(sql)

    def _create_table_rec_line(self):

        # TODO datetime
        sql = """CREATE TABLE IF NOT EXISTS '{self.REC_LINE_TABLE}' (
            line TEXT NOT NULL,
            point INTEGER NOT NULL,
            cable_id INTEGER NOT NULL,
            nchan INTEGER NOT NULL,
            PRIMARY KEY (line, point, cable_id));
            """.format(**locals())
        self.execute(sql)

        self._add_geom_linestringxy(self.REC_LINE_TABLE, 'rec_line')

    def _create_view_point_list(self):
        # TODO datetime

        sql = """CREATE VIEW IF NOT EXISTS '{:}'
            AS SELECT DISTINCT line, point FROM '{:}' ORDER BY line, point"""\
                    .format(self.POINT_LIST_VIEW, self.COORD_TABLE)
        self.execute(sql)

    def _create_view_rec_line(self):

        sql = """CREATE VIEW IF NOT EXISTS '{:}' AS SELECT
            line, point, cable_id,
            DATETIME(t.surveyyear_epoch + (day_of_year - 1) * 86400,
                'unixepoch') AS datetime,
            count(chan) as nchan, MakeLine(rec_pt) as rec_line
            FROM '{:}'  INNER JOIN '_p190_surveyyear' AS t
            GROUP BY line, point, cable_id
            ORDER BY chan
            """.format(self.REC_LINE_VIEW, self.REC_PT_TABLE)
        self.execute(sql)

    def _create_view_src_line(self):

        sql = """CREATE VIEW IF NOT EXISTS '{:}' AS SELECT
            line, source_id, MakeLine(geom) AS src_line
            FROM '{:}' WHERE record_id='S'
            GROUP BY line, source_id
            """.format(self.SRC_LINE_VIEW, self.COORD_TABLE)
        self.execute(sql)

    def _create_view_src_rec(self):

        sql = """CREATE VIEW IF NOT EXISTS '{:}' AS SELECT
            r.rowid as rec_pt_rowid,
            r.line as line, r.point as point,
            DATETIME(t.surveyyear_epoch + (s.day_of_year - 1) * 86400,
                'unixepoch') AS datetime,
            r.cable_id as cable_id,
            r.chan as chan, s.geom as src_pt, r.rec_pt as rec_pt,
            Line_Interpolate_Point(MakeLine(s.geom, r.rec_pt), 0.5)
                AS mid_pt,
            DISTANCE(s.geom, r.rec_pt) AS offset,
            r.cable_depth AS rec_depth, s.water_depth_or_elev AS
            water_depth_or_elev
            FROM '{:}' as r INNER JOIN '{:}'
            as s INNER JOIN '_p190_surveyyear' AS t
            ON r.point=s.point WHERE s.record_id='S'
            """.format(self.SRC_REC_VIEW, self.REC_PT_TABLE,
                    self.COORD_TABLE, self.HDR_TABLE)
        self.execute(sql)

        sql = """INSERT OR REPLACE INTO 'views_geometry_columns'(view_name,
                view_geometry, view_rowid, f_table_name,
                f_geometry_column, read_only)
                VALUES('{:}', 'src_pt', 'rowid', '{:}', 'geom', 0)
                """.format(self.SRC_REC_VIEW, self.COORD_TABLE)
        self.execute(sql)

        sql = """INSERT OR REPLACE INTO 'views_geometry_columns'(view_name,
                view_geometry, view_rowid, f_table_name,
                f_geometry_column, read_only)
                VALUES('{:}', 'rec_pt', 'rowid', '{:}', 'rec_pt', 0)
                """.format(self.SRC_REC_VIEW, self.REC_PT_TABLE)
        self.execute(sql)

    def _create_view_midpt(self):
        """
        Creates a view with src, rec, and mid points
        """
        if self.SRC_REC_VIEW not in self.views:
            self._create_view_src_rec()

        sql = """CREATE VIEW IF NOT EXISTS '{:}' AS SELECT
            rec_pt_rowid, line, point, datetime, cable_id, chan, src_pt,
            rec_pt, rec_depth,
            Line_Interpolate_Point(MakeLine(src_pt, rec_pt), 0.5) as midpt
            FROM '{:}'""".format(self.MIDPT_VIEW, self.SRC_REC_VIEW)
        self.execute(sql)

    def  _drop_spatial_index_if_exists(self, table, column):
        """
        Removes spatial index for table.column

        Parameters
        ----------
        table: str
            Table name
        column: str
            Name of geometry field to index
        """
        if "idx_{:}_{:}".format(table, column) not in self.tables:
            return

        sql = "SELECT DisableSpatialIndex('{:}', '{:}')"\
                .format(table, column)
        self.execute(sql)

        for part in ['_node', '_parent', '_rowid', '']:
            sql = "DROP TABLE IF EXISTS 'idx_{:}_{:}{:}'"\
                    .format(table, column, part)
            self.execute(sql)

        self.execute("VACUUM")

    def _get_SQL_insert_all_fields(self, table):
        
        fields = self._get_fields(table)
        sql = "INSERT INTO '{:}'".format(table)
        sql += "(" + ", ".join(fields) + ")"
        sql += " VALUES(" + ", ".join(['?' for f in fields]) + ");"

        return sql

    def _get_SQL_insert_all_fields_with_geomfromtext(self, table,
            geomfields=['geom'], **kwargs):

        fields = [f for f in self._get_fields(table) if f not in geomfields]
        values = ['?' for f in fields]

        fields += geomfields
        values += ['GeomFromText(?, {:})'.format(self.INPUT_SRID)\
                for f in geomfields]

        if len(kwargs) > 0:
            idx = {}
            for i, f in enumerate(fields):
                idx[f] = i

            for k in kwargs:
                if k in idx:
                    values[idx[k]] = kwargs[k]

        sql = "INSERT INTO '{:}'".format(table)
        sql += "(" + ", ".join(fields) + ")"
        sql += " VALUES(" + ", ".join(values) + ");"

        return sql

    def _get_SQL_insert_all_fields_with_pointxy(self, table,
            geomfield='geom', **kwargs):
        
        msg = '_get_SQL_insert_all_fields_with_pointxy() will be replaced'
        msg += ' with _get_SQL_insert_all_fields_with_geomfromtext'
        raise warnings.DepreciationWarning(msg)

        return _get_SQL_insert_all_fields_with_geomfromtext(table,
                geomfields=[geomfield], **kwargs)
        
    def _get_SQL_insert_coord(self):

        return self._get_SQL_insert_all_fields_with_geomfromtext(
                self.COORD_TABLE)

    SQL_INSERT_COORD = property(fget=_get_SQL_insert_coord)

    def _get_SQL_insert_hdr(self):

        return self._get_SQL_insert_all_fields(self.HDR_TABLE)

    SQL_INSERT_HDR = property(fget=_get_SQL_insert_hdr)

    def _get_SQL_insert_rec(self):

        return self._get_SQL_insert_all_fields_with_geomfromtext(
                self.REC_PT_TABLE, geomfields=['rec_pt'])

    SQL_INSERT_REC = property(fget=_get_SQL_insert_rec)

    def _parse_hdr(self, line):
        
        # record_id, type_id, type_modifier, desc, value
        return [line[0: 1].strip(), line[1: 3].strip(), line[3: 5].strip(),
                line[5: 32].strip(), line[32: 80].strip()]

    def _parse_coord(self, line):

        # line, point, day_of_year, record_id, vessel_id,
        # source_id, tailbuoy_id, water_depth_or_elev, 
        # spare, spare2, geom
        return [line[1: 13], # line
                line[19: 25], # point
                str(float(line[70: 73]) + (float(line[73: 75])\
                        + float(line[75: 77])/60.\
                        + float(line[77: 79])/3600.)/24.), # day_of_year
                line[0: 1], # record_id
                line[16: 17], # vessel_id
                line[17: 18], # source_id
                line[18: 19], # tailbuoy_id
                line[64: 70], # water_depth_or_elev
                line[13: 16], line[79: 80],
                "POINT({:} {:})".format(line[46: 55], line[55: 64])]

    def _parse_rec(self, line):

        i2 = 1
        dat = [[], [], []]
        for i in [0, 1, 2]:
            i1 = i2
            i2 = (i + 1) * 26 + 1
            _line = line[i1:i2]
            if _line[3] == ' ':
                i -= 1
                break
                
            # chan, cable_id, cable_depth, geom
            dat[i] = [_line[0:4], line[79], _line[22:26],
                    "POINT({:} {:})".format(_line[4:13], _line[13:22])]

        return dat[0:i + 1]
    
    def _read_p190(self, file, read_header=True):
        
        sql = 'SELECT record_id FROM {:}'.format(self.COORD_ID_TABLE)
        coord_ids = [d[0] for d in self.execute(sql).fetchall()]

        hdr_sql = self.SQL_INSERT_HDR
        coord_sql = self.SQL_INSERT_COORD
        rec_sql = self.SQL_INSERT_REC
        for line in file:
            if line.startswith('EOF'):
                continue
            elif (line[0] == 'H') and read_header:
                self.execute(hdr_sql, self._parse_hdr(line), warn_only=True)
            elif line[0] in coord_ids:
                coords = self._parse_coord(line)
                self.execute(coord_sql, coords, warn_only=True)

                # update rec sql with line, point, day, hour, min, sec
                rec_sql = self._get_SQL_insert_all_fields_with_geomfromtext(
                        self.REC_PT_TABLE, line="'{:}'".format(coords[0]),
                        point=coords[1], day_of_year=coords[2],
                        geomfields=['rec_pt'])
            elif line[0] == 'R':
                self.executemany(rec_sql, self._parse_rec(line),
                        warn_only=True)
        
        self.commit()

    def calc_src_rec_midpoints(self, output_field='mid_pt'):
        """
        Calculate source-receiver midpoints and store them in the database
        table set by `REC_PT_TABLE`.

        Parameters
        ----------
        output_field: str, optional
            Name of the field to store midpoint geometries in. Default is
            `'mid_pt'`.
        """
        if "mid_pt" not in self._get_fields(self.SRC_REC_VIEW):
            sql = "DROP VIEW {:}".format(self.SRC_REC_VIEW)
            self.execute(sql)
            self._create_view_src_rec()

        logging.info('Calculating midpoints...')
        logging.info('...output data in {:}.{:}', self.REC_PT_TABLE,
                output_field)

        if output_field not in self._get_fields(self.REC_PT_TABLE):
            self._add_geom_pointxy(self.REC_PT_TABLE, output_field)

        try:
            insert_sql = """UPDATE '{self.REC_PT_TABLE}'
                SET {output_field}=(SELECT {self.SRC_REC_VIEW}.mid_pt
                    FROM {self.SRC_REC_VIEW}
                        WHERE {self.SRC_REC_VIEW}.rec_pt_rowid
                            = {self.REC_PT_TABLE}.rowid)"""\
                                    .format(**locals())
            self.execute(insert_sql)
            self.commit()
        except DatabaseIntegrityError as e:
            msg = "Inserting all mid points together failed with:"
            msg += " DatabaseIntegrityError: {:}".format(e.message)
            logging.info(msg)
            logging.info("Trying to insert record by record...")
        
            sql = """SELECT DISTINCT line, point, day_of_year, cable_id
                FROM {self.REC_PT_TABLE}""".format(**locals())
            dat = self.execute(sql).fetchall()
            
            for line, point, day_of_year, cable_id in dat:
                _insert_sql = insert_sql + " AND line='{:}' AND point={:}"\
                        + " AND day_of_year={:} AND cable_id={:}"
                _insert_sql = _insert_sql.format(line, point, day_of_year,
                        cable_id)

                try:
                    self.execute(_insert_sql)
                    self.commit()
                except DatabaseIntegrityError as e:
                    msg += "Inserting midpoints failed with:"
                    msg += " 'DatabaseIntegrityError: {:}'".format(e.message)
                    msg += " Setting midpoint to NULL"
                    logging.warn(msg)

                    _insert_sql = """UPDATE '{:}'
                        SET {:}=NULL WHERE line='{:}' AND point={:}
                        AND day_of_year={:} AND cable_id={:}
                        """.format(self.REC_PT_TABLE, output_field,
                                line, point, day_of_year, cable_id)
                    self.execute(_insert_sql)
                    self.commit()


    def read_p190(self, filename, append=True):
        """
        Read data from a UKOAA P190 file and store it in the database

        Parameters
        ----------
        filename: str
            Path to a P190 file to read data from
        append: bool, optional
            If `True` (default), data are added to the existing database.
            If `False`, existing database tables are replaced. Note that
            when appending, the existing header is not updated. This is
            useful for combining data from multiple P190 files, but caution
            should be used to ensure that the header is applicable to all
            records in the database.
        """

        add_hdr = True
        nhdr = self.count(self.HDR_TABLE)
        if (nhdr > 0) and append:
            add_hdr = False
        elif (nhdr > 0) and not append:
            for table in [self.HDR_TABLE, self.COORD_TABLE,
                    self.REC_PT_TABLE]:
                sql = 'DROP TABLE IF EXISTS {:}'.format(table)
                self.execute(sql)
            add_hdr = True
        else:
            add_hdr = True

        logging.info('Reading P190 data from: {:}', filename)
        file = open(filename, 'rb')
        self._read_p190(file, read_header=add_hdr)

    def create_rec_lines(self, replace=False):
        """
        Create line segments from receiever point groups.
        """
        if replace:
            sql = "DROP TABLE IF EXISTS '{:}'".format(self.REC_LINE_TABLE)
            self.execute(sql)
        
        self._create_table_rec_line()

        sql = """INSERT OR REPLACE INTO '{:}'(line, point, cable_id, nchan,
            rec_line) SELECT line, point, cable_id, count(chan) as nchan, 
            MakeLine(rec_pt) as rec_line FROM '{:}' GROUP BY line,
            point ORDER BY chan
            """.format(self.REC_LINE_TABLE, self.REC_PT_TABLE)
        self.execute(sql)
        self.commit()

