"""
Utilities for interacting with the Generic Mapping Tools software
"""
import numpy as np

SQL2GMT_FORMATS = {'INTEGER': 'integer', 'BLOB': 'string',
        'REAL': 'double', 'TEXT': 'string'}

def pad_for_gmt(value):
    """
    Pads values for use in GMT ASCII file data strings
    """
    if (type(value) == str) or (type(value) == unicode):
        return '"{:}"'.format(value)
    else:
        return value

def make_field_line(fields):
    """
    Formats a the field definition list for a GMT ASCII file

    Parameters
    ----------
    fields: array_like
        List of field names to include in the definition list

    Returns
    -------
    field_line: str
        Formatted filed line

    Examples
    --------
    >>> make_field_line(['date', 'time', 'name'])
    '@Ndate|time|name'
    """
    fields = np.atleast_1d(fields)
    return '@N' + '|'.join([str(f) for f in fields])

def make_data_type_line_from_sql(sql_types):
    """
    Formats a the field type definition list from SQL data types 

    Parameters
    ----------
    fields: array_like
        List of field names to include in the definition list

    Returns
    -------
    field_line: str
        Formatted filed line

    Examples
    --------
    >>> make_data_type_line_from_sql(['TEXT', 'BLOB', 'INTEGER', 'REAL'])
    '@Tstring|string|integer|double'
    """
    sql_types = np.atleast_1d(sql_types)
    return '@T' + '|'.join([SQL2GMT_FORMATS[t] for t in sql_types])
