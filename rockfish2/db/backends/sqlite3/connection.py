"""
Extensions to the SQLite database connection object.
"""
import os
import pandas as pd
from pandas.io import sql as psql
from rockfish2 import logging
from rockfish2.utils.loaders import get_resource_file
from rockfish2.db.backends.sqlite3.base import dbapi2, SPATIALITE_ENABLED,\
        OperationalError, IntegrityError, ConfigurationError

def _process_exception(exception, message, warn=False):

    if warn:
        logging.warn(message)
        return

    if exception.__class__.__name__ == 'OperationalError':
        raise DatabaseOperationalError(message)
    elif exception.__class__.__name__ == 'IntegrityError':
        raise DatabaseIntegrityError(message)
    else:
        raise DatabaseError(message)

class DatabaseError(Exception):
    """
    Raised if there is a problem acessing the SQLite database
    """
    pass

class DatabaseOperationalError(DatabaseError):
    """
    Raised if there is a problem with SQL code
    """
    pass

class DatabaseIntegrityError(DatabaseError):
    """
    Raised if executing SQL causes an IntegrtityError
    """
    pass


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

    def _get_fields(self, table):
        """
        Return a list of fields for a table.

        Parameters
        ----------
        table: str
            Name of table to get fields for.
        """
        return [str(row[1]) for row in self._get_pragma(table)]

    def _get_pragma(self, table):
        """
        Return the SQLite PRAGMA information.

        Parameters
        ----------
        table: str
            Name of table to get PRAGMA for.

        Returns
        -------
        pragma
            Result of pragma query
        """
        sql = 'PRAGMA table_info({:})'.format(table)
        return self.execute(sql).fetchall()

    def _get_primary_fields(self, table):
        """
        Return a list of primary fields for a table.

        Parameters
        ----------
        table: str
            Name of table to get primary fields for.
        """
        primary_fields = []
        for row in self._get_pragma(table):
            if row[5] != 0:
                primary_fields.append((row[5], row[1]))

        primary_fields.sort()

        return [f[1] for f in primary_fields]

    def _get_required_fields(self, table):
        """
        Return a list of fields that have NOT NULL set.

        Parameters
        ----------
        table: str
            Name of table to get required fields for.
        """
        required_fields = []
        for row in self._get_pragma(table):
            if row[3] == 1:
                required_fields.append(str(row[1]))
        return required_fields

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

    def count(self, table, **kwargs):
        """
        Get the number of rows in a table.

        Parameters
        ----------
        table: str
            Name of table to get count from.
        **kwargs
            Keyword arguments for WHERE statements in the query
        """
        sql = 'SELECT COUNT(*) FROM {:}'.format(table)
        if len(kwargs) > 0:
            values = ['{:}="{:}"'.format(k, kwargs[k]) for k in kwargs]
            sql += ' WHERE ' + ' and '.join(values)
        return self.execute(sql).fetchall()[0][0]

    def execute(self, *args, **kwargs):
        """
        Executes a SQL statement.
        """
        warn = kwargs.pop('warn_only', False)

        logging.debug('Executing SQL:\n{:}', *args)
        try:
            return dbapi2.Connection.execute(self, *args)
        except Exception as e:
            msg = "execute() failed with '{:}: {:}'"\
                    .format(e.__class__.__name__, e.message)
            msg += ' while executing: {:}'.format(*args)

            _process_exception(e, msg, warn=warn)

    def executemany(self, *args, **kwargs):
        """
        Executes a SQL statement.
        """
        warn = kwargs.pop('warn_only', False)

        logging.debug('Executing SQL:\n{:}', args[0])
        try:
            return dbapi2.Connection.executemany(self, *args)
        except Exception as e:
            msg = "executemany() failed with '{:}: {:}'"\
                    .format(e.__class__.__name__, e.message)
            msg += ' while executing: {:}'.format(args[0])
            
            _process_exception(e, msg, warn=warn)

    def read_sql(self, sql, **kwargs):
        """
        Executes a SQL statement and returns a :class:`pandas.DataFrame`

        Parameters
        ----------
        sql: str
            SQL to execute on the database
        **kwargs:
            Optional parameters for :meth:`pandas.io.sql.read_sql`

        Returns
        -------
        data: :class:`pandas.DataFrame`
            Data from the table
        """
        return psql.read_sql(sql, self, **kwargs)

    def read_table(self, table):
        """
        Reads all rows from a table and returns a
        :class:`pandas.DataFrame`

        Parameters
        ----------
        table: str
            Table name to read data from

        Returns
        -------
        data: :class:`pandas.DataFrame`
            Data from the table
        """
        sql = 'SELECT * FROM {:}'.format(table)
        dat = self.execute(sql).fetchall()
        if len(dat) > 0:
            return pd.DataFrame(dat, columns=self._get_fields(table))
        else:
            return psql.read_sql(sql, self)

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

    def insert(self, table, **kwargs):
        """
        Adds an entry to a table.

        Parameters
        ----------
        table: str
            Name of table to add data to.
        **kwargs
            field=value arguments for data to add to the table 
        """
        sql = 'INSERT INTO %s (%s)' \
              % (table, ', '.join([k for k in kwargs]))
        sql += ' VALUES (%s)' % ', '.join(['?' for k in kwargs])
        data = tuple([kwargs[k] for k in kwargs])
        self.execute(sql, data)
