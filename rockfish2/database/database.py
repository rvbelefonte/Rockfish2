"""
Database tools
"""
import os
import pandas as pd
from pandas.io import sql as psql
#from sqlitedict import SqliteDict
from rockfish2 import logging

#XXX dev
#from logbook import Logger
#logging = Logger('dev-database')

try:
    from pysqlite2 import dbapi2
except ImportError:
    from sqlite3 import dbapi2

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

    def __init__(self, database=':memory:', spatial=False,
            params_table=None):

        if os.path.isfile(database):
            logging.info('Connecting to existing database: {:}',
                    database)
        else:
            logging.info('Creating new database: {:}', database)

        dbapi2.Connection.__init__(self, database)
        self.row_factory = dbapi2.Row

        if params_table is not None:
            if database == ':memory:':
                self._PARAMS = {}
            else:
                # XXX overriding persisant parameter table for bugfix
                self._PARAMS = {}

                #XXX
                #logging.debug("Mapping parameters to database table '{:}'",
                #        params_table)
                #self._PARAMS = SqliteDict(os.path.abspath(database),
                #        tablename=params_table, autocommit=True)

            self.__dict__[params_table] = self._PARAMS

        if spatial:
            self._init_spatial()

    #def __setattr__(self, name, value):
    #    """
    #    Called when an attribute assignment is attempted. This is called
    #    instead of the normal mechanism (i.e. store the value in the instance
    #    dictionary). name is the attribute name, value is the value to be
    #    assigned to it.
    #    """
    #    if hasattr(self, '_PARAMS') and (name.lower() in self._PARAMS):
    #        # update value in params table
    #        self._PARAMS[name.lower()] = value
    #    else:
    #        # just set a normal attribute
    #        self.__dict__[name] = value

    #def __getattr__(self, name):
    #    """
    #    This method is only called if the attribute is not found in the usual
    #    places (i.e. not an instance attribute or not found in the class tree
    #    for self).
    #    """
    #    if name.lower() in self._PARAMS:
    #        return self._PARAMS[name.lower()]
    #    else:
    #        msg = "'{:}' object has no attribute '{:}'"\
    #              .format(self.__class__.__name__, name)
    #        raise AttributeError(msg)

    def _init_spatial(self):
        """
        Setup spatial database
        """
        self.enable_load_extension(True)
        logging.debug('Loading libspatialite')
        self.execute('SELECT load_extension("libspatialite")')

        if 'spatial_ref_sys' not in self.tables:
            logging.debug("Creating table 'spatial_ref_sys'")
            self.execute('SELECT InitSpatialMetadata()')

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

    def _create_table(self, table, fields, if_not_exists=True):
        """
        Shortcut function for creating new tables.

        Parameters
        ----------
        table: str
            Name of the table to create.
        fields: array_like
            Fields to include in the new table. Must be a list of
            (name, sql type, default value, is not null, is primary) tuples.
        """
        _fields = []
        _primary_fields = []
        for f in fields:
            #Build: name type [NOT NULL] [DEFAULT default_value]
            _fields.append('{:} {:}'.format(f[0], f[1]))
            if f[3] is True:
                # require NOT NULL
                _fields[-1] += ' NOT NULL'
            if f[4] is True:
                # add to list of primary keys
                _primary_fields.append(f[0])
            if f[2] is not None:
                # include default value
                _fields[-1] += ' DEFAULT %s' % f[2]
        sql = "CREATE TABLE"
        if if_not_exists:
            sql += " IF NOT EXISTS"
        sql += " '{:}'".format(table)
        sql += ' ('
        sql += ', '.join(_fields)
        if len(_primary_fields) > 0:
            sql += ', PRIMARY KEY (' + ', '.join(_primary_fields) + ') '
        sql += ');'
        self.execute(sql)

    def _get_fields(self, table):
        """
        Return a list of fields for a table.

        Parameters
        ----------
        table: str
            Name of table to get fields for.
        """
        return [str(row[1]) for row in self._get_pragma(table)]

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

    def _get_types(self, table):
        """
        Return dictionary of data types for fields in a table

        Parameters
        ----------
        table: str
            Name of table to get field data types for

        Returns
        _______
        type_dict: dict
            Dictionary of SQL data types indexed by field names
        """
        type_dict = {}
        for row in self._get_pragma(table):
            type_dict[row[1]] = row[2]
        return type_dict

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
