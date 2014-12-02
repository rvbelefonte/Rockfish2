"""
Tools for working with Computer Programs in Seismology velocity models
"""
import os
import numpy as np
import datetime
import pandas as pd
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from rockfish2 import logging
from rockfish2.models.profile import Profile


class CPSModel1d(Profile):

    def __init__(self, *args, **kwargs):

        self.NAME = kwargs.pop('name', '1D model')
        self.UNITS = kwargs.pop('units', 'KGS')
        self.ISOTROPY = kwargs.pop('isotropy', 'ISOTROPIC')
        self.SHAPE = kwargs.pop('shape', 'FLAT EARTH')
        self.DIM = kwargs.pop('dim', '1-D')

        Profile.__init__(self, *args, **kwargs)

    def __str__(self):

        return self.write()

    def write(self, path_or_buf=None, float_format='%10.6f', **kwargs):
        """
        Write profile to the Computer Programs in Seismology model format
        
        Parameters
        ----------
        path_or_buf : string or file handle, default None
            File path or object, if None is provided the result is returned as
            a string.
        """
        model = self.model.copy()
        col = ['hr'] + [k for k in model if k != 'hr']
        model['hr'] = np.concatenate((np.diff(np.asarray(model.index)), [0.0]))
        model.index = np.arange(len(model))
        #model = model[0:len(model) - 1]

        sng = "MODEL\n"
        sng += "{:}\n".format(self.NAME)
        sng += "{:}\n".format(self.ISOTROPY)
        sng += "{:}\n".format(self.UNITS)
        sng += "{:}\n".format(self.SHAPE)
        sng += "{:}\n".format(self.DIM)
        sng += "CONSTANT VELOCITY\n"
        sng += "#\n"
        sng += "Created by: {:}{:}\n"\
                .format(self.__module__, self.__class__.__name__)
        sng += "Created on: {:}\n".format(datetime.datetime.now())
        sng += "#\n"
        sng += model[col].to_csv(sep='\t', index=False,
                float_format=float_format, **kwargs)

        if path_or_buf is None:
            return sng
        
        if hasattr(path_or_buf, 'write'):
            path_or_buf.write(sng)

        else:
            f = open(path_or_buf, 'w')
            f.write(sng)

    def read(self, filename, sep='\t'):
        """
        Write profile from the Computer Programs in Seismology model format
        """
        f = open(filename, 'rb')
        kind = f.readline().replace('\n', '')
        assert kind.startswith('MODEL'),\
                'File does not appear to be CPS format'
        self.NAME = f.readline().replace('\n', '')
        self.ISOTROPY = f.readline().replace('\n', '')
        self.UNITS = f.readline().replace('\n', '')
        self.SHAPE = f.readline().replace('\n', '')
        self.DIM = f.readline().replace('\n', '')
        _ = f.readline().replace('\n', '')
        _ = f.readline().replace('\n', '')
        _ = f.readline().replace('\n', '')
        _ = f.readline().replace('\n', '')
        _ = f.readline().replace('\n', '')
        cols = f.readline().replace('\n', '').split()
        
        self.model = pd.read_csv(filename, sep=sep, skiprows=11,
                index_col=0)

        try:
            dz = self.model.index[:]
            z = np.cumsum(np.asarray(dz)) - dz[0]
            if z[-1] == 0:
                z[-1] = dz[-2]

            self.model.index = z
            self.model.index.name = 'depth'

        except:
            pass
