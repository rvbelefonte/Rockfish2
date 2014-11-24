"""
General utilities for working with SQL database
"""
import numpy as np
import copy

def isnumeric(value):
    """
    Test if a string can be converted into a number
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

def py2str(values):
    """
    Convert python variables to strings for use in SQLite statements.

    Parameters
    ----------
    values: array_like
        List of values to convert.

    Returns
    -------
    strings
        List of strings.

    Examples
    --------
    >>> py2str([1.22, 'howdy', u'this is unicode'])
    ['1.22', "'howdy'", "'this is unicode'"]
    >>> py2str(np.atleast_1d([1.22, 'howdy', u'this is unicode']))
    ['1.22', "'howdy'", "'this is unicode'"]
    >>> py2str(np.arange(5))
    ['0', '1', '2', '3', '4']
    """
    if type(values) in [str, unicode]:
        values = [values]
    strings = []
    for v in values:
        if isnumeric(v):
            strings.append(str(v))
        else:
            strings.append("'{:}'".format(v))
    return strings

def format_where(match_dict, list_op='OR', key_op='AND', op='=',
        valid_fields=[]):
    """
    Format a dictionary of search terms into a SQLite search string.

    Parameters
    ----------
    match_dict : dict
        Keywords and values to match.
    list_op : str, optional
        SQLite operator to use when combining multiple values for a single key.
    key_op : str, optional
        SQLite operator to use when combining multiple values.
    valid_fields: array_like, optional
        List of valid fields to include in the search string. Default is to
        include all fields in `match_dict`.

    Returns
    -------
    sql : str
        SQLite query

    Examples
    --------
    >>> format_where({'field1': [1, 2, 3], 'field2': 'foo'})
    "(field2='foo') AND (field1=1 OR field1=2 OR field1=3)"
    >>> format_where({'field1': [1, 2, 3], 'field2': 'foo'}, list_op='AND')
    "(field2='foo') AND (field1=1 AND field1=2 AND field1=3)"
    >>> format_where({'field1': [1, 2, 3], 'field2': 'foo'}, key_op='OR')
    "(field2='foo') OR (field1=1 OR field1=2 OR field1=3)"
    >>> format_where({'field1': 1, 'field2': 2}, valid_fields=['field1'])
    '(field1=1)'
    >>> format_where({'field1': ('>', 1), 'field2': [2, 3, 4]})
    '(field2=2 OR field2=3 OR field2=4) AND (field1>1)'
    >>> format_where({'field': 1}, valid_fields=['field99'])
    ''
    """
    if len(valid_fields) == 0:
        valid_fields = [k for k in match_dict]

    fields = []
    _list_op = ' ' + list_op + ' '
    keys = [k for k in match_dict if k in valid_fields]
    for k in keys:
        _values = match_dict[k]
        if type(_values) == tuple:
            _op = _values[0]
            _values = np.atleast_1d(_values[1])
        else:
            _op = copy.copy(op)
            _values = np.atleast_1d(_values)

        values = ['{:}{:}{:}'.format(k, _op, v) for v in py2str(_values)]
        #except TypeError:
        #    values = ['{:}{:}{:}'.format(k, _op, py2str([match_dict[k]])[0])]

        fields.append('(' + _list_op.join(values) + ')')
    _key_op = ' ' + key_op + ' '
    sql = _key_op.join(fields)
    return sql
