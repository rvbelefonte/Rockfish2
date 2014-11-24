"""
Binning utilities for P190 navigation databases
"""
import numpy as np
from scipy.interpolate import interp1d
from rockfish2 import logging
from rockfish2.database.database import DatabaseError
from rockfish2.navigation.utils.cartesian import dist, cumdist,\
    distribute, build_rectangular_bins


class P190Binning(object):
    """
    Convenience class for binning utilities
    """
    def _create_bin_line(self, easting, northing, spacing,
        interp_kind='linear'):
        """
        Distributes stations evenly along a line
        """
        # distance along the line
        r0 = cumdist(easting, northing)
        r1 = np.arange(0, r0[-1], spacing)

        # distance to coords
        r2x = interp1d(r0, easting, kind=interp_kind)
        r2y = interp1d(r0, northing, kind=interp_kind)

        return r1, r2x(r1), r2y(r1)

    def _calc_bin_rectangles(self, easting, northing, inline_dimension,
            crossline_dimension):

        return build_rectangular_bins(easting, northing, inline_dimension,
            crossline_dimension)

    def _create_cmp_assignments_view(self):
        """
        Create a view that matches CMP assignments with src, rec pairs
        """
        if 'mid_pt' not in self._get_fields(self.REC_PT_TABLE):
            self.calc_src_rec_midpoints()

        if self.CMP_ASSIGNMENTS_VIEW in self.views:
            return

        logging.info("Creating view '{:}'...", self.CMP_ASSIGNMENTS_VIEW)
        sql = """CREATE VIEW '{self.CMP_ASSIGNMENTS_VIEW}'
            AS SELECT r.line as line, r.point as point, r.cable_id as cable_id,
            r.chan as chan, r.rec_pt as rec_pt, r.mid_pt as mid_pt,
            b.bin FROM '{self.REC_PT_TABLE}' as r
            NATURAL JOIN '{self.CMP_ASSIGNMENTS}' as b
            """.format(**locals())
        self.execute(sql)

        sql = """INSERT OR REPLACE INTO 'views_geometry_columns'(view_name,
                view_geometry, view_rowid, f_table_name,
                f_geometry_column, read_only)
                VALUES('{self.CMP_ASSIGNMENTS_VIEW}', 'mid_pt', 'rowid',
                    '{self.REC_PT_TABLE}', 'mid_pt', 0)""".format(**locals())
        self.execute(sql)
        self.commit()

    def assign_cmp_bins(self, spatial_index=True, **kwargs):
        """
        Assign midpoints to bins
        """
        if 'mid_pt' not in self._get_fields(self.REC_PT_TABLE):
            self.calc_src_rec_midpoints()
        
        logging.info('Assigning midpoints to {:}.{:}...',
                self.CMP_MODEL, 'bin_geom')

        if spatial_index:
            logging.info('...creating spatial indices')

            fields = [(self.CMP_MODEL, 'bin_geom'),
                      (self.REC_PT_TABLE, 'mid_pt')]

            for t, f in fields:
                logging.info('......{:}.{:}', t, f)
                sql = "SELECT CreateSpatialIndex('{:}', '{:}')".format(t, f)
                self.execute(sql)


        sql = """CREATE TABLE IF NOT EXISTS '{self.CMP_ASSIGNMENTS}' (
            line INTEGER NOT NULL,
            point INTEGER NOT NULL,
            cable_id INTEGER NOT NULL,
            chan INTEGER NOT NULL,
            bin INTEGER NOT NULL)""".format(**locals())
        self.execute(sql)

        self._add_geom_pointxy(self.CMP_ASSIGNMENTS, 'mid_pt')

        sql = """INSERT INTO '{self.CMP_ASSIGNMENTS}'
            (line, point, cable_id, chan, bin, mid_pt) SELECT
            r.line, r.point, r.cable_id, r.chan, b.bin, r.mid_pt FROM
            {self.REC_PT_TABLE} as r, {self.CMP_MODEL} as b WHERE
            ST_Contains(b.bin_geom, r.mid_pt)""".format(**locals())

        if spatial_index:
            sql += """ AND r.rowid IN (SELECT rowid FROM SpatialIndex
                WHERE f_table_name='{self.REC_PT_TABLE}' AND
                search_frame=b.bin_geom)""".format(**locals())
        
        self.execute(sql)
        self.commit()

        logging.info('...assigned {:} of {:} points to bins',
                self.count(self.CMP_ASSIGNMENTS),
                self.count(self.REC_PT_TABLE))

        self._create_cmp_assignments_view()

    def create_bin_line(self, easting, northing, spacing=6.25, bin0=1000,
            if_exists='fail', bin_center_field='bin_center',
            bin_polygon_field='bin_geom', bin_shape=None,
            interp_kind='linear', **kwargs):
        """
        Evenly distribute bins along a line

        TODO docs!
        """
        table = kwargs.pop('cmp_model', self.CMP_MODEL)
        inline_dimension = kwargs.pop('inline_dimension', spacing)
        crossline_dimension = kwargs.pop('crossline_dimension', 500)

        if if_exists == 'replace':
            sql = "DROP TABLE IF EXISTS {:}".format(table)
            self.execute(sql)

        if (table in self.tables) and (if_exists != 'append'):
            msg = "Table '{:}' exists. To replace or append existing data,"
            msg += " use if_exists='replace' or 'append'.".format(table)
            raise DatabaseError(msg)

        sql = """CREATE TABLE IF NOT EXISTS '{:}' (
	   bin INTEGER NOT NULL,
           offset REAL,
           PRIMARY KEY (bin))""".format(table)
        self.execute(sql)

        geomfields = [bin_center_field]
        if bin_center_field not in self._get_fields(table):
            self._add_geom_pointxy(table, bin_center_field)

        if bin_shape is not None:
            geomfields += [bin_polygon_field]
            if bin_polygon_field not in self._get_fields(table):
                self._add_geom_polyxy(table, bin_polygon_field)

        # layout bin centers
        logging.info('Creating bin line...')
        logging.info('...spacing = {:}', spacing)
        offset, x, y = self._create_bin_line(easting, northing, spacing,
                interp_kind=interp_kind)
        pts = ['POINT({:} {:})'.format(_x, _y) for _x, _y in zip(x, y)]
        logging.info('...defined {:} bin centers', len(pts))
        ibin = bin0 + np.arange(len(x))
        values = [ibin, offset, pts]

        # add bin outlines
        if bin_shape == 'rect':
            logging.info('...building {:}x{:} rectangular bins...',
                    inline_dimension, crossline_dimension)
            _polys = self._calc_bin_rectangles(x, y, inline_dimension,
                    crossline_dimension)
            polys = ['POLYGON(({:} {:}, {:} {:}, {:} {:}, {:} {:}))'\
                    .format(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
                        r[0], r[1]) for r in zip(*_polys)]
            logging.info('......defined {:} bin shapes', len(polys))
            values += [polys]

        # add bins to database
        sql = self._get_SQL_insert_all_fields_with_geomfromtext(table,
                geomfields=geomfields)

        self.executemany(sql, zip(*values))
        self.commit()

    def create_bin_line_from_midpoints(self, step=1, **kwargs):
        """
        Evenly distribute bins along a line connecting source-receiver
        midpoints

        Parameters
        ----------
        step: int, optional
            Interval between midpoints to use in creating the bin line.
            Default is `1` (i.e., include every point). 
        **kwargs: optional
            Keyword arguments. See :meth:`~P190Binning.create_bin_line`
            for details.
        """
        logging.info('Selecting midpoint coordinates...')

        sql = """DROP VIEW IF EXISTS temp_mp_line"""
        self.execute(sql)

        sql = """CREATE TEMPORARY VIEW temp_mp_line AS SELECT
            Line_Interpolate_Point({self.REC_LINE_VIEW}.rec_line, 0.5)
                AS pt FROM {self.REC_LINE_VIEW}
                ORDER BY {self.REC_LINE_VIEW}.point
            """.format(**locals())
        self.execute(sql)

        sql = """SELECT X(pt), Y(pt) FROM temp_mp_line"""
        dat = self.execute(sql).fetchall()

        easting = [dat[i][0] for i in range(0, len(dat) - 1, step)]
        northing = [dat[i][1] for i in range(0, len(dat) - 1, step)]

        easting += [dat[-1][0]]
        northing += [dat[-1][1]]

        logging.info('... found {:} points', len(easting))

        self.create_bin_line(easting, northing, **kwargs)
