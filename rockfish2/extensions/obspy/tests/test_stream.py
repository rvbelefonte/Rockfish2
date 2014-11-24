"""
Test suite for the obspy.stream module
"""
import os
import doctest
import unittest
import inspect
import copy
import numpy as np
import matplotlib.pyplot as plt
from obspy import read as obspy_read, Stream as ObspyStream, Trace
from rockfish2.utils.loaders import get_example_file
from rockfish2.extensions.obspy import stream

PLOT = True

class streamTestCase(unittest.TestCase):
    """
    Tests for the navigation.p190.io module
    """
    def test_init(self):
        """
        Should initialize a new Stream instance
        """
        st = stream.Stream()

        # should have obspy.Stream methods
        attr = inspect.getmembers(ObspyStream)
        for a in attr:
            self.assertTrue(hasattr(st, a[0]))

    def test_read(self):
        """
        Should read data into a new Stream instance
        """
        fname = get_example_file('ELZ_1hr.msd')
        st = stream.read(fname)
        self.assertTrue(isinstance(st, stream.Stream))

    def test_normalize_default(self):
        """
        Calling normalize with defaults should behave like obspy normalize
        method 
        """
        fname = get_example_file('ELZ_1hr.msd')
        st0 = stream.read(fname)
        st1 = obspy_read(fname)

        st0.normalize()
        st1.normalize()
        for tr0, tr1 in zip(st0.traces, st1.traces):
            self.assertEqual(min(tr0.data), min(tr1.data))
            self.assertEqual(max(tr0.data), max(tr1.data))

    def test_normalize_onebit(self):
        """
        Should run one-bit normalization on data
        """
        fname = get_example_file('ELZ_1hr.msd')
        st = stream.read(fname)

        st.normalize(method='onebit')

        for tr in st.traces:
            self.assertEqual(min(tr.data), -1)
            self.assertEqual(max(tr.data), 1)

    def test_normalize_stalta(self):
        """
        Should remove events
        """
        fname = get_example_file('ELZ_1hr.msd')
        st = stream.read(fname)
        st.detrend()
        st.demean()
        tr0 = st.traces[0].copy()
        tr0.stats['channel'] = 'BEFORE'

        # should work with defaults
        st.traces[0].stats['channel'] = 'AFTER'
        st.normalize(method='stalta')

        st.extend([tr0])

        self.assertGreater(st.traces[1].data.max(), st.traces[0].data.max())
        
        if PLOT:
            st.plot()

    def test_whiten(self):
        """
        Should whiten frequency spectra
        """
        fname = get_example_file('ELZ_1hr.msd')
        st = stream.read(fname)
        st.detrend()
        st.demean()
        st.traces[0].stats['channel'] = 'BEFORE'
        tr0 = st.traces[0].copy()

        # should work with defaults
        _st = stream.Stream()
        _st.extend([tr0])
        _st.traces[0].stats['channel'] = 'AFTER-No smooth'
        _st.whiten()
        tr1 = _st.traces[0].copy()
        st.extend([tr1])

        # should smooth normalization function
        _st = stream.Stream()
        _st.extend([tr0])
        _st.traces[0].stats['channel'] = 'AFTER-Smooth 10'
        _st.whiten(smooth=10)
        tr1 = _st.traces[0].copy()
        st.extend([tr1])

        # should also apply filter 
        _st = stream.Stream()
        _st.extend([tr0])
        _st.traces[0].stats['channel'] = 'AFTER-Filter'
        _st.whiten(smooth=10, apply_filter=(4, 6, 8))
        tr1 = _st.traces[0].copy()
        st.extend([tr1])

        if PLOT:
            st.spectra()
            st.plot(equal_scale=False)

    def dev_xcorr(self):
        """
        Should calculate cross correlations
        """
        fname = get_example_file('ELZ_10min.msd')
        st = stream.read(fname)

        print st

        # phase-lagged sign wave
        tr = st.traces[0].copy()

        npts = len(tr.data)
        dt = 1. / tr.stats['sampling_rate']

        lamb = tr.stats['sampling_rate'] * 2.

        lag = - tr.stats['sampling_rate'] * 0.5 
        t = dt * np.arange(0, npts)

        noise = lambda t: 2. * 10 * (np.random.rand(len(t)) - 0.5)

        a = np.cos(2 * np.pi * 1. / lamb * t) + noise(t)
        b = np.cos(2 * np.pi * 1. / lamb * (t + lag)) + noise(t)

        st.traces[0].data = a
        st.traces[0].stats['channel'] = 'A'
        st.extend([tr])
        st.traces[-1].data = b
        st.traces[-1].stats['channel'] = 'B'

        # should cross correlate everything with everything (except auto)
        xc = st.xcorr()

        if PLOT:
            xc.plot()












    
def suite():
    testSuite = unittest.makeSuite(streamTestCase, 'dev')
    testSuite.addTest(doctest.DocTestSuite(stream))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
