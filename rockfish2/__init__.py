"""
Rockfish2 -- Migration of well-tested components from original Rockfish library

**This repository is hosted on igsagiegwsnmim0, for now.  Rockfish
(original) is on github**
"""
from rockfish2.utils.loaders import get_example_file
from rockfish2.utils.version import get_version as _get_version
from rockfish2.utils.logging import RockfishLogger

_version_number = (1, 0, 0, 'alpha', 0)
__version__ = _get_version(_version_number)

logging = RockfishLogger('rockfish', level=2)

def _test():
    """
    Run full test suite
    """
    from rockfish2.tests.test_rockfish2 import tests, testRunner
    testRunner.run(tests)
