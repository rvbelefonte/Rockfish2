"""
SQLite3 backend for rockfish.

Works with either the pysqlite2 module or the sqlite3 module in the
standard Python library.
"""
from rockfish2 import logging

# XXX dev
#from logbook import Logger
#logging = Logger('dev-base', level=0)

try:
    try:
        from pyspatialite import dbapi2
        logging.debug('Using pyspatialite...')
        SPATIALITE_ENABLED = True
    except ImportError:
        try:
            from pysqlite2 import dbapi2
            logging.debug('Using pysqlite2...')
        except ImportError:
            from sqlite3 import dbapi2
            logging.debug('Using sqlite3 from standard library...')
except ImportError as exc:
    msg = "Error loading either pysqlite2 or sqlite3 module (tried in"
    msg += " that order): {:}".format(exc)
    raise ImportError(msg)

# Check if we can use the spatialite extension
if not SPATIALITE_ENABLED:
    try:
        _db = dbapi2.Connection(':memory:')
        if hasattr(_db, 'enable_load_extension'):
            _db.enable_load_extension(True)

        try:
            _db.execute('SELECT load_extension("mod_spatialite")')
            logging.debug('... found mod_spatialite')
        except:
            _db.execute('SELECT load_extension("libspatialite")')
            logging.debug('... found libspatialite')

        SPATIALITE_ENABLED = True
        logging.debug('... spatialite ENABLED')
    except dbapi2.OperationalError:
        SPATIALITE_ENABLED = False

logging.debug('SPATIALITE_ENABLED={:}'.format(SPATIALITE_ENABLED))

# Exceptions
OperationalError = dbapi2.OperationalError
IntegrityError = dbapi2.IntegrityError

class ConfigurationError(Exception):
    """
    Raised if there is a problem with the database driver configuration
    """
    pass
