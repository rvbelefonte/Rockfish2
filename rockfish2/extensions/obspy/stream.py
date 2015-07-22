"""
Extension to :mod:`obspy.core.stream`
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft, ifft, fftshift, ifftshift
from scipy.interpolate import interp1d
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
            _apply = kwargs.get('apply', True)
            sta = kwargs.get('sta', 3.)
            lta = kwargs.get('lta', 10.)
            trigger_on = kwargs.get('trigger_on', 1.1)
            trigger_off = kwargs.get('trigger_off', 1.0)
            for tr in self.traces:
                df = tr.stats['sampling_rate']
                _sta = int(sta * df)
                _lta = int(lta * df)

                cft = trigger.recSTALTA(tr.data, _sta, _lta)
                tr.trg = trigger.triggerOnset(cft, trigger_on, trigger_off)
                
                if _apply:
                    for on, off in tr.trg:
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
        tr.stats['nstack'] = ntrc
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

    def mirror(self, norm=2, trim=False, **kwargs):
        """
        Sum each trace with a time-reversed copy of itself.

        Parameters
        ----------
        norm: scalar, optional
            Value to normalize the sum by. Default is `2` (i.e., the mean
            is taken).
        trim: bool, optional
            Determines wether or not to discard half of the trace. If
            `True`, `data = data[npts/2:]`. Default is `False` (i.e., the
            entire summed trace is returned.
        kwargs: keyword_arguments, optional
            Keyword arguments used to select traces to mirror. Default
            is to mirror all traces in the stream.

        Returns
        -------
        stream: :class:`rockfish2.extensions.obspy.stream.Stream`
            Stream containing mirrored traces.
        """
        if len(kwargs) > 0:
            st = self.select(**kwargs)
        else:
            st = self

        for tr in st:
            tr.data = (tr.data + tr.data[::-1]) / norm

            if trim:
                tr.data = tr.data[len(tr.data) / 2:]

        return st

    def transform_ft(self, differentiate=False, hilbert=True, omega0=None,
            alpha=10, lag_time=False, mirror_time=False,
            plot=True, figsize=None, ylim=None, plot_func=np.abs, norm=True,
            vmin=None, vmax=None, xlabel=None, ylabel=None, title=None,
            show=True, **kwargs):
        """
        Decompose waveforms into the frequency-time domain.

        The output grids are used in frequency-time analysis (FTAN) and are
        thus often referred to as "FTAN images."


        Parameters 
        ----------
        differentiate: bool, optional
            Determines whether or not to calculate the decomposition using the
            time derivative of traces. Default is `'False'`.  Note that, in
            ambient noise analysis, the time derivative of the noise
            correlation function is the so-called empirical Green's
            function.
        hilbert: bool, optional
            Determines whether or not to calculate the decomposition on the
            Hilbert transform (i.e., envelope) of traces. Default is `'True'`.
        omega0: array_like, optional
            Sets center frequencies for the decomposition. Default is an
            array from the minimum to the maximum frequency resolved by
            each trace.
        alpha: number, optional
            Sets the width of the Gaussian filters, defined as
            `np.exp(-alpha * (((omega - omega0) / omega0) ** 2`.
        lag_time: bool, optional
            If `True`, time is assumed to be "lag time" with center sample
            at t = 0. Default is `False`.
        mirror_time: bool, optional
            Determines whether or not to take the average of the forward
            and reversed time columns. Default is `False`.
        kwargs: keyword_arguments, optional
            Keyword arguments used to select traces to transform. Default
            is to transform all traces in the stream.

        Plot parameters
        ---------------
        plot: bool, optional
            Determines whether or not to plot the transformed data. Default
            is `True`.
        figsize : tuple of integers, optional
            width, height in inches. If not provided, defaults to
            the :mod:`matplotlib` default figure size.
        ylim: list, optional
            Sets time range to plot. Default is to plot the entire time
            range. Only applies to the plot (i.e., the full time series is
            transformed).
        plot_func: callable, optional
            Function that calculates data to plot. Must take a 2D array as
            the only argument and return a real value. Default is
            :meth:`numpy.abs` (i.e., the magnitude of the complex transform
            data is plotted).
        norm: bool, optional
            Determines whether or not to plot normalized image data.
        vmin, vmax : scalar, optional, default: None
            Set the minimum and/or maximum clip values for plotting the
            image data.
        xlabel: str, optional
            Set the *x* axis label of the current axis.
        ylabel: str, optional
            Set the *y* axis label of the current axis.
        show: bool, optional
            Determines whether or not to show the plot. Default is `True`.
            Set to `False` to add additional objects to the plot.

        Returns
        -------
        stream: :class:`rockfish2.extensions.obspy.stream.Stream`
            Stream containing traces with new attributes `Stream.trace.ft`
            (frequency-time transformed data), `Stream.trace.omega0`
            (center frequencies for columns in `ft`), and `Stream.trace.t`
            (times for rows in `ft`). If kwargs are given, the output
            stream will only contain traces selected by
            `Stream.select(**kwargs)`. If no kwargs are given, traces are
            modified in place, and also returned. 
        """
        if len(kwargs) > 0:
            st = self.select(**kwargs)
        else:
            st = self

        gaussian = lambda omega, omega0, alpha:\
                np.exp(-alpha * (((omega - omega0) / omega0) ** 2))

        if plot:
            fig = plt.figure(figsize=figsize)
            nplt = len(st.traces)

            if xlabel is None:
                xlabel = 'Frequency (Hz)'

            if ylabel is None:
                if lag_time:
                    ylabel = 'Lag time (s)'
                else:
                    ylabel = 'Time (s)'
        
        for itr, tr in enumerate(st.traces):
            npts = len(tr.data)
            dt = 1. / tr.stats['sampling_rate']
            t = dt * np.arange(npts)

            if lag_time:
                t -= dt * npts / 2.

            omega = np.fft.fftfreq(npts, d=dt)

            if omega0 is None:
                _omega0 = np.arange(min(omega), max(omega) + 0.1, 0.1)
            else:
                _omega0 = np.atleast_1d(omega0)
        
            if differentiate:
                d = 1j * omega
            else:
                d = 1.

            if hilbert:
                d *= (1. + np.sign(omega))

            s = tr.data
            S = np.fft.fft(s) * d

            G = np.asarray([gaussian(omega, w0, alpha) for w0 in _omega0]) 

            ft = np.fliplr(np.fft.ifft(S * d * G))

            if mirror_time:
                amp = np.real(ft)
                phi = np.imag(ft)

                amp = (amp + np.fliplr(amp)) / 2.
                phi = (phi + np.fliplr(phi)) / 2.

                ft = amp + 1j * phi

            tr.ft = ft
            tr.omega0 = _omega0
            tr.t = t

            if plot:
                ax = fig.add_subplot(nplt, 1, itr + 1)

                xlim = [min(_omega0), max(_omega0)]

                if ylim is None:
                    _ylim = [min(t), max(t)]
                else:
                    _ylim = ylim

                xdim = np.float(xlim[1] - xlim[0])
                ydim = np.float(_ylim[1] - _ylim[0])

                img = plot_func(tr.ft)
                
                if norm:
                    img /= np.max(np.abs(img))

                ax.imshow(img.T, extent=[min(omega0), max(omega0),
                    min(t), max(t)], aspect=xdim/ydim, vmin=vmin, vmax=vmax)

                plt.ylim(_ylim)
                plt.xlim(xlim)

                plt.xlabel(xlabel)
                plt.ylabel(ylabel)

                if title is None:
                    plt.title(tr.id)
                else:
                    plt.title(title)

        if plot and show:
            plt.show()

        return st

    def transform_fv(self, vel=None, offset=None, plot=True, figsize=None,
            ylim=None, group=True, phase=True, norm=True, vmin=None, vmax=None,
            xlabel=None, title=None, show=True,**kwargs):
        """
        Transform data into the frequency-velocity domain
        """
        st = self.transform_ft(self, plot=False, **kwargs)

        if plot:
            fig = plt.figure(figsize=figsize)
            nrow = len(st.traces)
            ncol = np.sum([group, phase])
            iplt = 0

            if xlabel is None:
                xlabel = 'Frequency (Hz)'

        for tr in st:
            if offset is None:
                try:
                    x = tr.stats['offset']
                except KeyError:
                    msg = "offset must be given as a keyword argument or"
                    msg += " set by Trace.stats['offset']"
                    raise ValueError(msg)
            else:
                x = offset
            
            v0 = np.clip(x / tr.t, 0., 1e30)

            if vel is None:
                idx = np.nonzero(v0 < 1e30)[0]
                vi = np.linspace(min(v0), max(v0[idx]), 500)
            else:
                vi = vel

            amp = np.real(tr.ft)
            phi = np.imag(tr.ft)

            fv = np.zeros((len(tr.omega0), len(vi)), np.complex)
            for iw, w in enumerate(tr.omega0):
    
                v2amp = interp1d(v0, amp[iw, :])
                v2phi = interp1d(v0, phi[iw, :])
                fv[iw, :] = v2amp(vi) + 1j * v2phi(vi)

            tr.v = vi
            tr.fv = fv

            if plot:
                xlim = [min(tr.omega0), max(tr.omega0)]
                if ylim is None:
                    _ylim = [min(vi), max(vi)]
                else:
                    _ylim = ylim

                xdim = np.float(xlim[1] - xlim[0])
                ydim = np.float(_ylim[1] - _ylim[0])

                if group:
                    iplt += 1
                    ax = fig.add_subplot(nrow, ncol, iplt)

                    img = np.abs(fv)**2

                    if norm:
                        img /= np.max(img)
                
                    ax.imshow(img.T, extent=[min(tr.omega0), max(tr.omega0),
                        min(vi), max(vi)], aspect=xdim/ydim,
                        vmin=vmin, vmax=vmax)

                    plt.ylim(_ylim)
                    plt.xlim(xlim)

                    plt.ylabel('Group velocity (m/s)')
                    plt.xlabel(xlabel)

                    if title is None:
                        plt.title(tr.id)
                    else:
                        plt.title(title)

        if plot and show:
            plt.show()

        return st
