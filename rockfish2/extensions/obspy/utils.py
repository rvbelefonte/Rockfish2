"""
Utilities for the ObsPy extension
"""
import numpy as np
from scipy.signal import iirfilter, freqz


def fill_array(data, mask=None, fill_value=None):
    """
    Fill masked numpy array with value without demasking.
    
    Additonally set fill_value to value.
    If data is not a MaskedArray returns silently data. 
    """
    if mask is not None and mask is not False:
        data = np.ma.MaskedArray(data, mask=mask, copy=False)
    if np.ma.is_masked(data) and fill_value is not None:
        data._data[data.mask] = fill_value
        np.ma.set_fill_value(data, fill_value)
    elif not np.ma.is_masked(data):
        data = np.ma.filled(data)
    return data

def bandpass_response(freqmin, freqmax, corners=2, zerophase=False, sr=None,
        N=None, whole=False):
    """
    Butterworth-Bandpass Filter.

    Filter frequency data from freqmin to freqmax using
    corners corners.
    :param data: Data to filter, type numpy.ndarray.
    :param freqmin: Pass band low corner frequency.
    :param freqmax: Pass band high corner frequency.
    :param sr: Sampling rate in Hz.
    :param corners: Filter corners. Note: This is twice the value of PITSA's 
        filter sections
    :param zerophase: If True, apply filter once forwards and once backwards.
        This results in twice the number of corners but zero phase shift in
        the resulting filtered trace.
    :return: Filtered data.
    
    Derived from obspy.signal.filter
    """
    df = sr
    fe = 0.5 * df
    low = freqmin / fe
    high = freqmax / fe
    # raise for some bad scenarios
    if high > 1:
        high = 1.0
        msg = "Selected high corner frequency is above Nyquist. " + \
              "Setting Nyquist as high corner."
        warnings.warn(msg)
    if low > 1:
        msg = "Selected low corner frequency is above Nyquist."
        raise ValueError(msg)
    [b, a] = iirfilter(corners, [low, high], btype='band',
                       ftype='butter', output='ba')
    freqs, values = freqz(b, a, N, whole=whole)  # @UnusedVariable
    if zerophase:
        values *= np.conjugate(values)
    return freqs, values

def smooth(x, window_len, window='flat'):
    """smooth the data using a window with requested size.
    
    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal 
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.
    
    input:
        x: the input signal 
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.
    output:
        the smoothed signal
        
    example:
    t=linspace(-2,2,0.1)
    x=sin(t)+randn(len(t))*0.1
    y=smooth(x)
    
    see also: 
    
    numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    scipy.signal.lfilter
    
    http://www.scipy.org/Cookbook/SignalSmooth
    """

    # window_len = 2 * window_len + 1
    if window_len % 2 == 0:
        window_len += 1
    if x.ndim != 1:
        raise ValueError, "smooth only accepts 1 dimension arrays."
    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."
    if window_len < 3:
        return x
    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is one of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"
    s = np.r_[x[(window_len - 1) // 2 :0:-1], x, x[-1:-(window_len + 1) // 2:-1]]
    if window == 'flat':  # moving average
        w = np.ones(window_len, 'd')
    else:
        w = getattr(np, window)(window_len)
    y = np.convolve(w / w.sum(), s, mode='valid')
    return y
