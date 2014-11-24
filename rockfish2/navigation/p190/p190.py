"""
Class for working with P190 seismic navigation data
"""
from rockfish2.navigation.p190.database import P190Database
from rockfish2.navigation.p190.binning import P190Binning


class P190(P190Database, P190Binning):
    """
    Class for working with P190 seismic navigation data
    """
    def __init__(self, cmp_model='cmp_line', 
            cmp_assignments='cmp_assignments',
            cmp_assignments_view='cmp_assignments_view', **kwargs):

        P190Database.__init__(self, **kwargs)

        params = locals()
        for k in params:
            if k not in ['self', 'kwargs']:
                self.p190_params[k] = params[k]
