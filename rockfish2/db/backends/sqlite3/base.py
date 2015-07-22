"""
SQLite3 backend for rockfish.

Works with either the pysqlite2 module or the sqlite3 module in the
standard Python library.
"""
from rockfish2 import logging

# XXX dev
#from logbook import Logger
#logging = Logger('dev-base', level=0)

MOD_SPATIALITE_PATHS = ['mod_spatialite',
    '/usr/local/lib/mod_spatialite.so']


class ConfigurationError(Exception):
    """
    Raised if there is a problem with the database driver configuration
    """
    pass


SPATIALITE_ENABLED = False
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
def load_spatialite(db):

    if hasattr(db, 'enable_load_extension'):
        db.enable_load_extension(True)

    for p in MOD_SPATIALITE_PATHS:
        try:
            db.load_extension(p)
            logging.debug('... found {:}'.format(p))
            return
        except:
            pass

    raise ConfigurationError('Could not find any of: {:}'\
            .format(MOD_SPATIALITE_PATHS))


logging.debug('SPATIALITE_ENABLED={:}'.format(SPATIALITE_ENABLED))

# Exceptions
OperationalError = dbapi2.OperationalError
IntegrityError = dbapi2.IntegrityError

