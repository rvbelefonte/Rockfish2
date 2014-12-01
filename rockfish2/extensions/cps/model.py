"""
Tools for working with Computer Programs in Seismology velocity models
"""
import os
import numpy as np
import datetime
import subprocess
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from rockfish2 import logging
from rockfish2.models.profile import Profile


class CPSModel1d(Profile):

    def __init__(self, *args, **kwargs):

        self.NAME = kwargs.pop('name', '1D model')
        self.UNITS = kwargs.pop('units', 'KGS')
        self.ISOTROPY = kwargs.pop('isotropy', 'ISOTROPIC')

        Profile.__init__(self, *args, **kwargs)

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
        model = model[0:len(model) - 1]

        sng = "MODEL\n"
        sng += "{:}\n".format(self.NAME)
        sng += "{:}\n".format(self.ISOTROPY)
        sng += "{:}\n".format(self.UNITS)
        sng += "FLAT EARTH\n"
        sng += "1-D\n"
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


    # TODO move these to class CPS, which will have CPS.model =
    # CPSModel1d()
    def _sprep96(self, model_path='cps_data'):
        """
        Create input file for calculating dispersion curves
        """
        if not os.path.isdir(model_path):
            os.mkdir(model_path)
        
        modfile = os.path.join(model_path, 'model.dat')
        logging.info('Writing CPS model file to: {:}', modfile)
        self.write(modfile)

        sh = "sprep96 -M {:} -DT 1.0 -NPTS 2 -L -R -NMOD 2"\
                .format(modfile)

        subprocess.call(sh, shell=True)

    def calc_dispersion(self):
        """
        Calculate dispersion curves
        """
        # TODO
        raise NotImplementedError
