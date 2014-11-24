"""
Logger configuration
"""
import os
import platform
import multiprocessing
from collections import OrderedDict
import logbook

BANNER_WIDTH = 70

class RockfishLogger(logbook.Logger):

    def __init__(self, *args, **kwargs):

        logbook.Logger.__init__(self, *args, **kwargs)
    
        self.banner0 = BANNER_WIDTH * '='

    def header(self):
        
        from rockfish2 import __version__, __file__
        
        self.info('\n{:}\nRockfish -- Version {:}\n{:}',
                self.banner0, __version__, self.banner0)

        self.debug('Logger: {:} ({:})', logbook.__name__, logbook.__version__)
        self.debug('Log level: {:}', self.level_name)
        self.log_system_info(level=1)

    def _get_system_info(self):
        """
        Log information about the system 
        """
        stats = OrderedDict()
        stats['Python version'] = platform.python_version()
        stats['Python compiler'] = platform.python_compiler()
        stats['System'] = platform.system()
        stats['Machine'] = platform.machine()
        stats['Processor'] = platform.processor()
        stats['CPU count'] = multiprocessing.cpu_count()
        stats['Architecture'] = platform.architecture()[0]
        stats['Node'] = platform.node()

        return stats

    system_info = property(fget=_get_system_info)

    def log_system_info(self, level=1):
        """
        Log system information
        """
        stats = self.system_info
        for stat in stats:
            self.log(level, '{:}: {:}', stat, stats[stat])

