"""
Cartesian geometry utilities
"""
import numpy as np
from rockfish2 import logging
from scipy.interpolate import interp1d

def dist(x0, y0, x1, y1):
    """
    Calculate cartestian distance from (x0, y0) to points in (x1, y1)

    Parameters
    ----------
    x0, y0: number
        Coordinates of origin point
    x1, y1: array_like
        Coordinates of points to calculate distance from (x0, y0) for.

    Returns
    -------
    distance: numpy.ndarray
        A new array containing distances from (x0, y0) to each point in
        (x1, y1).

    Examples
    --------
    >>> dist(0, 0, [1], [1])
    array([ 1.41421356])
    """
    dx = np.atleast_1d(x1) - x0
    dy = np.atleast_1d(y1) - y0
    return np.sqrt(dx ** 2 + dy ** 2)


def cumdist(x, y):
    """
    Calculate cumlative cartestian distance along a line

    Parameters
    ----------
    x, y: array_like
        Input x- and y-coordinate arrays defining a line.  Arrays must be
        of equal length.

    Returns
    -------
    dist: numpy.ndarray
        A new array containing cumulative distance along a line defined
        by `x`, `y`.

    Examples
    --------
    >>> cumdist([0, 1, 2, 3], [0, 1, 2, 3])
    array([ 0.        ,  1.41421356,  2.82842712,  4.24264069])
    """
    assert len(x) == len(y), 'Arrays must have the same length'
    
    dx = np.diff(x)
    dy = np.diff(y)
    
    r = np.zeros(len(x))
    r[1:] = np.cumsum(np.sqrt(dx ** 2 + dy ** 2))
    
    return r

def distribute(x, y, offsets, interp_kind='linear', bounds_error=True):
    """
    Distribute points along a line defined by x, y coordinates.
    
    Parameters
    ----------
    x, y: array_like
        Input x- and y-coordinate arrays defining a line.  Arrays must be
        of equal length.
    offsets: array_like
        Input array of distances along the line to calculate coordinates
        for.
    interp_kind: str or int, optional
        Specifies the kind of interpolation as a string
        ('linear', 'nearest', 'zero', 'slinear', 'quadratic, 'cubic'
        where 'slinear', 'quadratic' and 'cubic' refer to a spline
        interpolation of first, second or third order) or as an integer
        specifying the order of the spline interpolator to use.
        Default is 'linear'. See :mod:`scipy.interpolate.interp1d` for more
        information.

    Returns
    -------
    x1, y1: ndarray
        x- and y-coordinates of the new points along the line.

    Examples
    --------
    >>> x = [10, 20, 21, 36, 45]
    >>> y = [1, 2, 4, 5, 6]
    >>> length = max(cumdist(x, y))
    >>> print length
    36.3746251151
    >>> offsets = np.linspace(0, length, 5)
    >>> print offsets
    [  0.           9.09365628  18.18731256  27.28096884  36.37462512]
    >>> x1, y1 = distribute(x, y, offsets)
    >>> print x1
    [ 10.          19.04852619  26.88829836  35.96181362  45.        ]
    >>> print y1
    [ 1.          1.90485262  4.39255322  4.99745424  6.        ]
    """
    offsets0 = cumdist(x, y)
    r2x = interp1d(offsets0, x, kind=interp_kind, bounds_error=bounds_error)
    r2y = interp1d(offsets0, y, kind=interp_kind, bounds_error=bounds_error)

    try:
        x1 = r2x(offsets)
        y1 = r2y(offsets)

    except ValueError as e:
        if max(offsets) > max(offsets0):
            msg = e.message + ' max(offsets) = {:} > {:}.'\
                    .format(max(offsets), max(offsets0))
        elif min(offsets) < min(offsets0):
            msg = e.message + ' min(offsets) = {:} < {:}.'\
                    .format(min(offsets), min(offsets0))
        raise ValueError(msg)

    return x1, y1

def _rotate_point(rot, x, y):
    pt1 = rot * np.matrix([[x], [y]])
    return pt1[0, 0], pt1[1, 0]

def build_rectangular_bins(x, y, dx, dy, theta=[]):
    """
    Calculate corner coordinates for rectangles along a line

    TODO docs
    """
    nbin = len(x)
    ibin = range(nbin)
    assert len(y) == nbin, 'len(x) must equal len(y)'

    # rotation angle of the bins at each point
    theta = np.atleast_1d(theta)
    if len(theta) == 0:
        theta = np.zeros(len(x))
        theta[0:-1] = np.arctan2(np.diff(y), np.diff(x))
        theta[-1] = theta[-2]
    elif len(theta) == 1:
        theta = theta[0] * np.ones(nbin)
    else:
        assert len(theta) == nbin,\
            'theta must be a scalar value or a list with length = len(x)'

    # rotation matrices
    _rot = np.asarray([[np.cos(theta), -np.sin(theta)],
        [np.sin(theta), np.cos(theta)]])
    rot = [np.asmatrix(_rot[0:2, 0:2, i]) for i in ibin]

    # offsets
    deltx = dx / 2. * np.ones(nbin)
    delty = dy / 2. * np.ones(nbin)

    d1 = np.asarray([_rotate_point(_rot, _x, _y)\
            for _rot, _x, _y in zip(rot, -deltx, delty)])
    d2 = np.asarray([_rotate_point(_rot, _x, _y)\
            for _rot, _x, _y in zip(rot, deltx, delty)])
    d3 = np.asarray([_rotate_point(_rot, _x, _y)\
            for _rot, _x, _y in zip(rot, deltx, -delty)])
    d4 = np.asarray([_rotate_point(_rot, _x, _y)\
            for _rot, _x, _y in zip(rot, -deltx, -delty)])

    # coordinate lists
    x1 = x + d1[:, 0]
    x2 = x + d2[:, 0]
    x3 = x + d3[:, 0]
    x4 = x + d4[:, 0]

    y1 = y + d1[:, 1]
    y2 = y + d2[:, 1]
    y3 = y + d3[:, 1]
    y4 = y + d4[:, 1]

    return x1, y1, x2, y2, x3, y3, x4, y4
