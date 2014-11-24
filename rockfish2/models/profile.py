"""
Utilities for working with 1-dimensional models
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d


class Profile(object):

    def __init__(self, data=None, index=None, index_name=None,
            columns=None, **kwargs):

        self.model = pd.DataFrame(data=data, index=index, columns=columns)

        if index_name is not None:
            self.model.index.name = index_name

    def _interp_nyquist(self, vfield='Vp', fmax=50, nsamp=2, kind='linear'):
        """
        Interpolates values into layers with a thicknesses required to
        approximate a velocity-depth function parameterized by a stack of
        linear gradient layers.
        """
        if vfield not in self.model:
            msg = """'{:}' is not defined in the model. Set vfield equal to
                one of: {:}""".format(vfield, self.model.columns).strip()
            raise KeyError(msg)

        lyrs = self.to_layers().model
        nlyr = len(lyrs)

        # calc dz nyquist
        dz = lyrs[lyrs.columns[2]]
        v = np.asarray(self.model[vfield])
        dz_calc = np.zeros(nlyr)
        for ilyr in range(nlyr):
            v_min = np.min([v[ilyr], v[ilyr + 1]])
            lamb_min = v_min / fmax
            _dz_calc = lamb_min / nsamp
            dz_calc[ilyr] = np.min([dz[ilyr], _dz_calc])

        # populate z's
        ztop = np.asarray(lyrs[lyrs.columns[0]])
        zbot = np.asarray(lyrs[lyrs.columns[1]])
        z = np.asarray([])
        for ilyr in range(nlyr):
            _z = np.arange(ztop[ilyr], zbot[ilyr], dz_calc[ilyr])
            z = np.concatenate((z, _z))

        if z[-1] < zbot[-1]:
            z = np.concatenate((z, [zbot[-1]]))

        # interpolate
        z0 = self.model.index
        values = np.asarray([interp1d(z0, self.model[v], kind=kind)(z)\
                for v in self.model.columns]).T

        # build new model
        interp_model = pd.DataFrame(data=values, index=z,
                columns=self.model.columns)
        interp_model.index.name = self.model.index.name

        return interp_model

    def interp(self, method='nyquist', inplace=False, **kwargs):

        model = self.__getattribute__('_interp_' + method)(**kwargs)

        if inplace:
            self.model = model
        else:
            p = Profile()
            p.model = model
            return p

    def to_layers(self):

        n = len(self.model)

        idx = self.model.index
        dat = self.model.as_matrix().T
        values = np.asarray([[np.mean([v[i], v[i + 1]])\
                for i in range(n - 1)] for v in dat]).T

        columns = self.model.columns

        layers = Profile(data=values, columns=columns, index_name=None)
        layers.model[idx.name + '_top'] = idx[0:-1] 
        layers.model[idx.name + '_bot'] = idx[1:]
        layers.model[idx.name + '_delt'] = layers.model[idx.name + '_bot']\
                - layers.model[idx.name + '_top']

        columns = [idx.name + '_top', idx.name + '_bot', idx.name + '_delt'] +\
                list(self.model.columns)

        layers.model = layers.model[columns]

        return layers



    def plot(self, columns=None, figsize=(10, 5), invert_yaxis=True,
            fmt='.-b', layer_fmt='-k', layers=True):

        if columns is None:
            columns = self.model.columns

        fig = plt.figure(figsize=figsize)

        nplt = len(columns)
        ncol = int(np.ceil(np.sqrt(nplt)))
        nrow = int(np.floor(np.sqrt(nplt)))

        if layers:
            lyr = self.to_layers()
            nlyr = len(lyr.model)
            ctop = lyr.model.columns[0]
            cbot = lyr.model.columns[1]
            zlyr = np.asarray(zip(lyr.model[ctop],
                lyr.model[cbot])).flatten()
                
        iplt = 0
        for c in columns:
            iplt += 1
            ax = fig.add_subplot(nrow, ncol, iplt)
            ax.plot(self.model[c], self.model.index, fmt)

            if layers:
                vlyr = np.asarray(zip(lyr.model[c], lyr.model[c])).flatten()
                ax.plot(vlyr, zlyr, layer_fmt)

            if invert_yaxis:
                plt.gca().invert_yaxis()

            plt.xlabel(c)
            plt.ylabel(self.model.index.name)

        plt.show()
