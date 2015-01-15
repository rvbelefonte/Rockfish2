"""
Extensions to the SQLite database connection object.
"""
import os
import pandas as pd
from rockfish2 import logging
from rockfish2.utils.loaders import get_resource_file
from rockfish2.db.backends.sqlite3.base import dbapi2, SPATIALITE_ENABLED,\
        OperationalError, IntegrityError, ConfigurationError


class Connection(dbapi2.Connection):

    ConfigurationError = ConfigurationError

    def __init__(self, database=':memory:', spatial=False):

        if os.path.isfile(database):
            logging.info('Connecting to existing database: {:}',
                    database)
        else:
            logging.info('Creating new database: {:}', database)

        dbapi2.Connection.__init__(self, database)
        self.row_factory = dbapi2.Row

        if spatial:
            self.init_spatialite()

    def _get_tables(self):
        """
        Returns a list of tables in the database.
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        return [d[0] for d in self.execute(sql)]

    tables = property(_get_tables)

    def _get_views(self):
        """
        Returns a list of views in the database.
        """
        sql = "SELECT name FROM sqlite_master WHERE type='view'"
        return [d[0] for d in self.execute(sql)]

    views = property(_get_views)

    def init_spatialite(self):
        """
        Setup a spatialite database.
        """
        if not SPATIALITE_ENABLED:
            msg = "SQLite3 connection cannot load spatialite extensions or"
            msg += " extensions were not found."
            raise ConfigurationError(msg)

        if 'spatial_ref_sys' not in self.tables:
            self.execute('SELECT InitSpatialMetadata()')
            
            #XXX except OperationalError:
                # use custom sql for init
                # this is a work-around for spatialite versions lacking
                # InitSpatialMetadata
            #    init_sql_file =\
            #            get_resource_file('initspatialmetadata.sql')
            #    msg = 'Attempting to initialize new spatialite database'
            #    msg += ' from {:}'.format(init_sql_file)
            #    logging.debug(msg)

            #    f = open(init_sql_file, 'rb')
            #    sql = '\n'.join(f.readlines())

            #    self.executescript(sql)
            #    self.commit()
