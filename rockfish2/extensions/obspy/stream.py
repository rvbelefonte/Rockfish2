"""
Extension to :mod:`obspy.core.stream`
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft, ifft, fftshift, ifftshift
from obspy import read as _read, Stream as ObspyStream, Trace
from obspy.signal.util import nextpow2
from obspy.signal import trigger
from obspy.signal.cross_correlation import xcorr
from rockfish2.extensions.obspy.utils import fill_array, bandpass_response,\
        smooth as smooth_func
from rockfish2 import logging


def read(*args, **kwargs):
    """
    Read waveform files into a Stream object.

    See :meth:`obspy.read` for supported arguments
    """
    _st = _read(*args, **kwargs)

    st = Stream()
    st.traces = _st.traces

    return st


class Stream(ObspyStream):

    def __init__(self, *args, **kwargs):

        ObspyStream.__init__(self, *args, **kwargs)

    def demean(self, global_mean=False):
        """
        Subtract the mean of data from all traces
        """
        logging.info("Demeaning {:} traces...", len(self.traces)) 
        if global_mean:
            mean = np.mean(np.asarray([tr.data for tr in
                self.traces]).flatten())

        for tr in self.traces:
            if global_mean:
                tr.data -= mean
            else:
                tr.data -= np.mean(tr.data)

    def whiten(self, smooth=None, apply_filter=None):
        """
        Apply spectral whitening to data.
        """
        logging.info("Whitening {:} traces...", len(self.traces)) 
        for tr in self.traces:

            mask = np.ma.getmask(tr.data)
            N = len(tr.data)
            nfft = nextpow2(N)
            spec = fft(tr.data, nfft)

            df = tr.stats['sampling_rate']
            spec_ampl = np.sqrt(np.abs(np.multiply(spec, np.conjugate(spec))))

            if isinstance(smooth, basestring) and isnumber(smooth) and\
                    (smooth > 0):
                smooth = int(smooth * N / df)
                spec /= ifftshift(smooth_func(fftshift(spec_ampl), smooth))
            else:
                spec /= spec_ampl
            if apply_filter is not None:
                spec *= bandpass_response(*apply_filter, sr=df, N=len(spec),
                        whole=True)[1]
            ret = np.real(ifft(spec, nfft)[:N])
            tr.data = fill_array(ret, mask=mask, fill_value=0.)

    def normalize(self, method='trace_max', **kwargs):
        """
        Normalizes all trace in the stream.
        """
        logging.info("Normalizing {:} traces with method '{:}'...",
                len(self.traces), method)
        if method == 'trace_max':
            ObspyStream.normalize(self, global_max=False)
        elif method == 'global_max':
            ObspyStream.normalize(self, global_max=True)
        elif method == 'onebit':
            for tr in self.traces:
                tr.data = np.sign(tr.data)
        elif method == 'stalta':
            sta = kwargs.get('sta', 3.)
            lta = kwargs.get('sta', 10.)
            trigger_on = kwargs.get('trigger_on', 1.2)
            trigger_off = kwargs.get('trigger_off', 1.0)
            for tr in self.traces:
                _sta = int(tr.stats['sampling_rate'] * sta)
                _lta = int(tr.stats['sampling_rate'] * lta)
                cft = trigger.recSTALTA(tr.data, _sta, _lta)
                trg = trigger.triggerOnset(cft, trigger_on, trigger_off)
                for on, off in trg:
                    tr.data[on:off] = 0
        else:
            raise ValueError("Unknown method '{:}'".format(method))

    def spectra(self):
        """
        Calculate and plot frequency spectra of all traces
        """
        fig = plt.figure()
        nplt = len(self.traces)

        for itr, tr in enumerate(self.traces):

            spec = np.fft.fft(tr.data)
            npts = len(tr.data)
            dt = 1. / tr.stats['sampling_rate']
            freq = np.fft.fftfreq(npts, d=dt)

            i = np.argsort(freq)

            iplt = itr + 1
            ax = fig.add_subplot(nplt, 1, iplt)
            ax.semilogy(freq[i], np.abs(spec)[i], '-k')
            plt.xlim(min(freq), max(freq))
            plt.ylabel('Power')
            plt.title(tr.id)

        plt.xlabel('Frequency (Hz)')
        plt.show()

    def stack(self, **kwargs):

        st = self.select(**kwargs)

        tr = st.traces[0].copy()
        ntrc = len(st.traces)
        len0 = len(tr.data)
        for _tr in st.traces[1:]:
            n = min(len0, len(_tr.data))
            tr.data[0:n] += _tr.data[0:n]

        tr.data /= ntrc
        st.traces = [tr]

        return st

    def xcorr(self, itrace0=None, itrace1=None, shift_len=1001, 
            include_auto=False):
        """
        Cross correlate traces
        """
        if itrace0 is None:
            itrace0 = range(len(self.traces))

        if itrace1 is None:
            itrace1 = range(len(self.traces))

        st = Stream()

        if include_auto:
            k = 0
        else:
            k = 1

        i0, i1 = np.triu_indices(len(itrace0), k=k, m=len(itrace1))

        logging.info("Cross correlating {:} trace pairs...", len(self.traces))
        for _itr0, _itr1 in zip(i0, i1):
            itr0 = itrace0[_itr0]
            itr1 = itrace1[_itr1]

            tr0 = self.traces[itr0]
            tr1 = self.traces[itr1]

            assert tr0.stats['sampling_rate']\
                    == tr1.stats['sampling_rate'],\
                    'Sampling rates for traces {:} ({:}) and {:} ({:})'\
                            .format(itr0, tr0.id, itr1, tr1.id)\
                            + ' are not equal.'

            logging.info('... {:} with {:}...', tr0.id, tr1.id)
            
            i, c, _xc = xcorr(self.traces[itr1], self.traces[itr0],
                    shift_len, full_xcorr=True)

            xc = Trace(data=_xc, header=tr0.stats)
            xc.stats['npts'] = len(_xc)
            xc.stats['xcorr_imax'] = i
            xc.stats['xcorr_max'] = c

            for k in ['network', 'station', 'channel']:
                if tr0.stats[k] != tr1.stats[k]:
                    xc.stats[k] = '{:}-{:}'.format(tr0.stats[k],
                            tr1.stats[k])

            st.extend([xc])

        return st
