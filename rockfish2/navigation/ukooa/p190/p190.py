"""
Class for working with P190 seismic navigation data
"""
from rockfish2.navigation.ukooa.p190.database import P190Database
from rockfish2.navigation.ukooa.p190.binning import P190Binning


class P190(P190Database, P190Binning):
    """
    Class for working with P190 seismic navigation data
    """
    def __init__(self, cmp_model='cmp_line', 
            cmp_assignments='cmp_assignments',
            cmp_assignments_view='cmp_assignments_view', **kwargs):

        P190Database.__init__(self, **kwargs)

        self.CMP_MODEL = cmp_model
        self.CMP_ASSIGNMENTS = cmp_assignments
        self.CMP_ASSIGNMENTS_VIEW = cmp_assignments_view

    def __str__(self):
        """
        Print a summary of the P190 data
        """
        # TODO: print a summary based on describe_* functions
        raise NotImplementedError('Coming soon...')

    def describe_receivers(self, **kwargs):
        """
        Generate summary statistics from the receiver point table
        """
        # TODO
        raise NotImplementedError('Coming soon...')

    def describe_points(self, **kwargs):
        """
        Generate summary statistics from points table
        """
        # TODO
        raise NotImplementedError('Coming soon...')
