"""
Wrappers for running Computer Programs in Seismology
"""
import os
import shutil
import copy
import numpy as np
from collections import OrderedDict
import subprocess
import time
import matplotlib.pyplot as plt
from rockfish2 import logging
from rockfish2.extensions.cps.model import CPSModel1d

# XXX dev
from logbook import Logger
logging = Logger('cps-dev', level=0)

def get_flags(**kwargs):
    flags = []
    for k in kwargs:
        if type(kwargs[k]) is bool:
            if kwargs[k] == True:
                flags.append('-{:}'.format(k.upper()))
        else:
            flags.append('-{:} {:}'.format(k.upper(), kwargs[k]))
    return flags

def read_egn_txt(filename):

    f = open(filename, 'rb')

    i = -99999
    disp = []
    for iline, line in enumerate(f):
        i += 1

        try:
            dat = line.split()
            if len(dat) < 2:
                continue
        
            if dat[1] == 'WAVE':
                i = 0
                
                if dat[0] == 'RAYLEIGH':
                    skip = 2

                if dat[0] == 'LOVE':
                    skip = 3
        
                disp.append(OrderedDict())
                disp[-1]['kind'] = dat[0][0].upper() + dat[0].lower()[1:]
                disp[-1]['mode'] = dat[4]
                disp[-1]['T'] = []
                disp[-1]['f'] = []
                disp[-1]['c'] = []
                disp[-1]['u'] = []
        
                continue
        
            if i >= skip:
                fdat = [float(v) for v in dat]
                disp[-1]['T'].append(fdat[1])
                disp[-1]['f'].append(fdat[2])
                disp[-1]['c'].append(fdat[3])
                disp[-1]['u'].append(fdat[4])

        except Exception as e:
            msg = e.message + ' (File: {:}, line {:})'.format(filename, iline)
            raise IOError(msg)

    return disp


def read_der_txt(filename):

    f = open(filename, 'rb')

    i = -99999
    der = []
    for iline, line in enumerate(f):
        i += 1

        try:
            dat = line.split()
            if len(dat) < 2:
                continue
            
            if dat[1] == 'WAVE':
                i = 0
            
                der.append(OrderedDict())
                der[-1]['kind'] = dat[0][0].upper() + dat[0].lower()[1:]
                der[-1]['mode'] = dat[4]

                if der[-1]['kind'] == 'Rayleigh':
                    der[-1]['ur'] = []
                    der[-1]['tr'] = []
                    der[-1]['uz'] = []
                    der[-1]['tz'] = []
                    der[-1]['dcdh'] = []
                    der[-1]['dcda'] = []
                    der[-1]['dcdb'] = []
                    der[-1]['dcdr'] = []

                if der[-1]['kind'] == 'Love':
                    der[-1]['ut'] = []
                    der[-1]['tt'] = []
                    der[-1]['dcdh'] = []
                    der[-1]['dcdb'] = []
                    der[-1]['dcdr'] = []
            
                continue
            
            if dat[0] == 'T':
                der[-1]['freq'] = 1. / float(dat[2])
            
            if i >= 4:
                fdat = [float(v) for v in dat]

                if der[-1]['kind'] == 'Rayleigh':
                    der[-1]['ur'].append(fdat[1])
                    der[-1]['tr'].append(fdat[2])
                    der[-1]['uz'].append(fdat[3])
                    der[-1]['tz'].append(fdat[4])
                    der[-1]['dcdh'].append(fdat[5])
                    der[-1]['dcda'].append(fdat[6])
                    der[-1]['dcdb'].append(fdat[7])
                    der[-1]['dcdr'].append(fdat[8])
                
                if der[-1]['kind'] == 'Love':
                    der[-1]['ut'].append(fdat[1])
                    der[-1]['tt'].append(fdat[2])
                    der[-1]['dcdh'].append(fdat[3])
                    der[-1]['dcdb'].append(fdat[4])
                    der[-1]['dcdr'].append(fdat[5])

        except Exception as e:
            msg = e.message + ' (File: {:}, line {:})'.format(filename, iline)
            raise IOError(msg)

    return der



class CPSError(Exception):
    """
    Base exception class for errors when running CPS programs
    """
    pass

class CPS(CPSModel1d):
    """
    Class for running CPS programs on 1D models
    """
    def __init__(self, *args, **kwargs):

        CPSModel1d.__init__(self, *args, **kwargs)

        self._DIR = kwargs.pop('dir', self._get_tempdir(replace=True))
        self.FMAX = kwargs.pop('fmax', 10)

        self.CLEANUP = kwargs.pop('cleanup', True)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.CLEANUP:
            self.cleanup()

    def _get_tempdir(self, replace=False):

        wd = 'temp.CPS{:}'.format(int(time.time()))

        if os.path.isdir(wd) and replace:
            shutil.rmtree(wd)

        os.mkdir(wd)

        return os.path.abspath(wd)

    def _get_dir(self):
        return self._DIR

    def _set_dir(self, value):
        os.chdir(value)
        self._DIR = value

    DIR = property(fget=_get_dir, fset=_set_dir)

    def cleanup(self):

        dirname = os.path.basename(self.DIR)
        if os.path.isdir(self.DIR) and dirname.startswith('temp.CPS'):
            shutil.rmtree(self.DIR)
        
    def sprep96(self, love=True, rayleigh=True, npts=16, nmod=2,
            hs=0, hr=0, verbose=False, interp=False, **kwargs):
        """
        Create input file for calculating dispersion curves
        """
        wd = self.DIR
        model = kwargs.pop('model', 'model.dat')
        fmax = kwargs.pop('fmax', self.FMAX)
        dt = kwargs.pop('dt', 1 / (2. * fmax))

        if love:
            lov = '-L'
        else:
            lov = ''

        if rayleigh:
            ray = '-R'
        else:
            ray = ''

        if interp:
            logging.debug('Interpolating model for fmax = {:}', fmax)
            mod = copy.deepcopy(self)
            mod.interp(method='nyquist', vfield=['Vp', 'Vs'],
                    fmax=fmax, nsamp=2, inplace=True)
        else:
            mod = self

        logging.debug('len(model) = {:}', len(mod.model))
        mod.write(os.path.join(wd, model))

        assert os.path.isfile(os.path.join(wd, model)),\
                'Failed to write model to: ' + os.path.join(wd, model)

        sh = "cd {:}\n".format(wd)
        sh += """sprep96 -M {model} -DT {dt} -NPTS {npts} {lov} {ray}
            -NMOD {nmod} -HS {hs} -HR {hr}""".format(**locals())\
                    .replace('\n', '')

        logging.debug(sh)
        process = subprocess.Popen(sh, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise CPSError(err)

        if verbose:
            print out

        assert os.path.isfile(os.path.join(wd, 'sdisp96.dat')),\
                "sprep96 failed to produce 'sdisp96.dat'"

        return mod

    def sdisp96(self, verbose=False, **kwargs):
        """
        Calculate dispersion curves
        """
        wd = self.DIR

        sh = "cd {:}\n".format(self.DIR)
        sh += "sdisp96 -v " + ' '.join(get_flags(**kwargs))

        logging.debug(sh)

        process = subprocess.Popen(sh, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise CPSError(err)

        if verbose:
            print out

        if (not os.path.isfile(os.path.join(wd, 'sdisp96.lov')))\
            or (not os.path.isfile(os.path.join(wd, 'sdisp96.ray'))):
            msg = "sdisp96 did not produce 'sdisp96.lov' or 'sdisp96.ray'"
            logging.warn(msg)

    def scomb96(self, verbose=False, rename=False, **kwargs):
        """
        Repairs dispersion curves
        """
        wd = self.DIR

        sh = "cd {:}\n".format(self.DIR)
        sh += "scomb96 " + ' '.join(get_flags(**kwargs))

        logging.debug(sh)

        process = subprocess.Popen(sh, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise CPSError(err)

        if verbose:
            print out

        if "-R" in sh:
            assert os.path.isfile(os.path.join(wd, 'tsdisp96.ray')),\
                    "scomb96 failed to produce 'tsdisp96.ray'"
            if rename:
                src = os.path.join(wd, 'tsdisp96.ray')
                dst = os.path.join(wd, 'sdisp96.ray')
                shutil.move(src, dst)
        
        if "-L" in sh:
            assert os.path.isfile(os.path.join(wd, 'tsdisp96.lov')),\
                    "scomb96 failed to produce 'tsdisp96.lov'"
            if rename:
                src = os.path.join(wd, 'tsdisp96.lov')
                dst = os.path.join(wd, 'sdisp96.lov')
                shutil.move(src, dst)

    def sregn96(self, verbose=False, **kwargs):

        sh = "cd {:}\n".format(self.DIR)
        sh += "sregn96 " + ' '.join(get_flags(**kwargs))

        logging.debug(sh)

        process = subprocess.Popen(sh, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise CPSError(err)

        if verbose:
            print out
        
        if '-DER' in sh:
            assert os.path.isfile(os.path.join(self.DIR, 'sregn96.der')),\
                    "sregn96 failed to produce 'sregn96.der'"
        else:
            assert os.path.isfile(os.path.join(self.DIR, 'sregn96.egn')),\
                  "sregn96 failed to produce 'sregn96.egn'"

    def slegn96(self, verbose=False, **kwargs):

        sh = "cd {:}\n".format(self.DIR)
        sh += "slegn96 " + ' '.join(get_flags(**kwargs))

        logging.debug(sh)

        process = subprocess.Popen(sh, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise CPSError(err)

        if verbose:
            print out
        
        if '-DER' in sh:
            assert os.path.isfile(os.path.join(self.DIR, 'slegn96.der')),\
                    "slegn96 failed to produce 'sregn96.der'"
        else:
            assert os.path.isfile(os.path.join(self.DIR, 'slegn96.egn')),\
                  "slegn96 failed to produce 'slegn96.egn'"

    def sdpder96(self, verbose=False, **kwargs):

        sh = "cd {:}\n".format(self.DIR)
        sh += "sdpder96 " + ' '.join(get_flags(**kwargs))

        logging.debug(sh)

        process = subprocess.Popen(sh, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise CPSError(err)

        if verbose:
            print out
        
        if ('-L' in sh) and ('-TXT' in sh):
            assert os.path.isfile(os.path.join(self.DIR, 'SLDER.TXT')),\
                    "sdpder96 failed to produce 'SLDER.TXT'"

        if ('-R' in sh) and ('-TXT' in sh):
            assert os.path.isfile(os.path.join(self.DIR, 'SRDER.TXT')),\
                    "sdpder96 failed to produce 'SRDER.TXT'"

    def sdpegn96(self, verbose=False, **kwargs):

        sh = "cd {:}\n".format(self.DIR)
        sh += "sdpegn96 " + ' '.join(get_flags(**kwargs))

        logging.debug(sh)

        process = subprocess.Popen(sh, shell=True, stdout=subprocess.PIPE)
        out, err = process.communicate()

        if err:
            raise CPSError(err)

        if verbose:
            print out
        
        #if ('-L' in sh) and ('-TXT' in sh):
        #    assert os.path.isfile(os.path.join(self.DIR, 'SLDER.TXT')),\
        #            "sdpder96 failed to produce 'SLDER.TXT'"

        #if ('-R' in sh) and ('-TXT' in sh):
        #    assert os.path.isfile(os.path.join(self.DIR, 'SRDER.TXT')),\
        #            "sdpder96 failed to produce 'SRDER.TXT'"

    def calc_dispersion(self, hs=0, hr=0, love=True, rayleigh=True,
            npts=16, nmod=2, verbose=False, interp=False, repairs=[],
            **kwargs):
        """
        Calculate dispersion curves
        """
        logging.debug('locals = {:}', locals())
        if love:
            L = True
        else:
            L = False
        
        if rayleigh:
            R = True
        else:
            R = False

        fmax = kwargs.pop('fmax', self.FMAX)
        dt = kwargs.pop('dt', 1 / (2. * fmax))
        fmax = 1 / (2. * dt)  # force consistency between dt and fmax

        logging.debug('fmax = {:}, dt = {:}', fmax, dt)

        mod = self.sprep96(L=L, R=R, fmax=fmax, dt=dt, npts=npts, nmod=nmod,
                hs=hs, hr=hr, verbose=verbose, interp=interp)
        self.sdisp96(verbose=verbose)

        if len(repairs) > 0:
            logging.debug('Running repairs with scomb96...')
            for opt in repairs:
                self.scomb96(rename=True, **opt)

        disp = []
        if R:
            self.sregn96() #XXX hs=hs, hr=hr) should have these from sprep
            self.sdpegn96(R=True, C=True, txt=True)
            disp += read_egn_txt(os.path.join(self.DIR, 'SREGN.TXT'))
        
        if L:
            self.slegn96() #XXX hs=hs, hr=hr) should have these from sprep
            self.sdpegn96(L=True, C=True, txt=True)
            disp += read_egn_txt(os.path.join(self.DIR, 'SLEGN.TXT'))

        return disp

    def calc_der(self, hs=0, hr=0, love=True, rayleigh=True,
            npts=16, nmod=2, verbose=False, interp=False, **kwargs):

        if love:
            L = True
        else:
            L = False
        
        if rayleigh:
            R = True
        else:
            R = False

        logging.debug('locals: {:}', locals())

        fmax = kwargs.pop('fmax', self.FMAX)
        dt = kwargs.pop('dt', 1 / (2. * fmax))
        fmax = 1 / (2. * dt)  # force consistency between dt and fmax

        logging.debug('fmax = {:}, dt = {:}', fmax, dt)

        mod = self.sprep96(L=L, R=R, fmax=fmax, dt=dt, npts=npts, nmod=nmod,
                hs=hs, hr=hr, verbose=verbose, interp=interp)
        self.sdisp96(verbose=verbose)

        der = []
        if R:
            self.sregn96(hs=hs, hr=hr, der=True)
            self.sdpder96(R=True, C=True, txt=True)
            der += read_der_txt(os.path.join(self.DIR, 'SRDER.TXT'))
        
        if L:
            self.slegn96(hs=hs, hr=hr, der=True)
            self.sdpder96(L=True, C=True, txt=True)
            der += read_der_txt(os.path.join(self.DIR, 'SLDER.TXT'))

        return mod, der

    def plot_der(self, *args, **kwargs):
        """
        Plot depth-dependent quantities 
        """
        show = kwargs.pop('show', True)

        mod, der = self.calc_der(*args, **kwargs)

        interp = kwargs.pop('interp', False)
        love = kwargs.pop('love', True)
        rayleigh = kwargs.pop('rayleigh', True)

        depth = mod.model.index

        if rayleigh:
            fig = plt.figure()
            plt.suptitle('Rayleigh waves')
            
            ax1 = fig.add_subplot(241)
            plt.gca().invert_yaxis()
            plt.xlabel('UZ')
            plt.ylabel('Depth (km)')
            
            ax2 = fig.add_subplot(242)
            plt.gca().invert_yaxis()
            plt.xlabel('UR')
            
            ax3 = fig.add_subplot(243)
            plt.gca().invert_yaxis()
            plt.xlabel('TR')
            
            ax4 = fig.add_subplot(244)
            plt.gca().invert_yaxis()
            plt.xlabel('TZ')
            
            ax5 = fig.add_subplot(245)
            plt.gca().invert_yaxis()
            plt.xlabel('DC/DH')
            plt.ylabel('Depth (km)')
            
            ax6 = fig.add_subplot(246)
            plt.gca().invert_yaxis()
            plt.xlabel('DC/DA')

            ax7 = fig.add_subplot(247)
            plt.gca().invert_yaxis()
            plt.xlabel('DC/DB')

            ax8 = fig.add_subplot(248)
            plt.gca().invert_yaxis()
            plt.xlabel('DC/DR')

            for f in der:
                if f['kind'] == 'Rayleigh':
                    ax1.plot(f['uz'], depth)
                    ax2.plot(f['ur'], depth)
                    ax3.plot(f['tr'], depth)
                    ax4.plot(f['tz'], depth)
                    ax5.plot(f['dcdh'], depth)
                    ax6.plot(f['dcda'], depth)
                    ax7.plot(f['dcdb'], depth)
                    ax8.plot(f['dcdr'], depth)


        if love:
            fig = plt.figure()
            plt.suptitle('Love waves')

            ax1 = fig.add_subplot(231)
            plt.gca().invert_yaxis()
            plt.xlabel('UT')
            plt.ylabel('Depth (km)')
            
            ax2 = fig.add_subplot(232)
            plt.gca().invert_yaxis()
            plt.xlabel('TT')
            
            ax3 = fig.add_subplot(233)
            plt.gca().invert_yaxis()
            plt.xlabel('DC/DH')
            
            ax4 = fig.add_subplot(234)
            plt.gca().invert_yaxis()
            plt.xlabel('DC/DB')
            plt.ylabel('Depth (km)')
            
            ax5 = fig.add_subplot(235)
            plt.gca().invert_yaxis()
            plt.xlabel('DC/DR')
            plt.ylabel('Depth (km)')

            for f in der:
                if f['kind'] == 'Love':
                    ax1.plot(f['ut'], depth)
                    ax2.plot(f['tt'], depth)
                    ax3.plot(f['dcdh'], depth)
                    ax4.plot(f['dcdb'], depth)
                    ax5.plot(f['dcdr'], depth)

        mod.plot(show=False)

        if show:
            plt.show()

        return mod, der


    def plot_dispersion(self, *args, **kwargs):
        """
        Plot dispersion curves
        """
        show = kwargs.pop('show', True)
        xlim = kwargs.pop('xlim', None)
        ylim = kwargs.pop('ylim', None)
        period = kwargs.pop('period', False)
        semilogx = kwargs.pop('semilogx', False)
        rayleigh_color = kwargs.pop('rayleigh_color', 'r')
        love_color = kwargs.pop('love_color', 'b')
        phase = kwargs.pop('phase', True)
        group = kwargs.pop('group', True)
        if 'ax' in kwargs:
            ax = kwargs.pop('ax')
            show = False
        else:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        disp = self.calc_dispersion(*args, **kwargs)

        if semilogx:
            plot = ax.semilogx
        else:
            plot = ax.plot

        for phase in disp:
            if phase['kind'] == 'Rayleigh':
                c = rayleigh_color
            if phase['kind'] == 'Love':
                c = love_color

            if period:
                x = phase['T']
            else:
                x = phase['f']
            
            if phase:
                plot(x, np.asarray(phase['c']), '-' + c,
                        label='{:}, mode {:} (phase)'.format(phase['kind'],
                            phase['mode']))
            if group:
                plot(x, np.asarray(phase['u']), '--' + c,
                        label='{:}, mode {:} (group)'.format(phase['kind'],
                           phase['mode']))

        if xlim:
            plt.xlim(xlim)

        if ylim:
            plt.ylim(ylim)


        #plt.legend()
        if period:
            plt.xlabel('Period (s)')
        else:
            plt.xlabel('Frequency (Hz)')

        plt.ylabel('Velocity (km/s)')

        if show:
            plt.show()

        return disp

    def plot_disp(self, *args, **kwargs):
        """
        Plot dispersion curves
        """
        return self.plot_dispersion(*args, **kwargs)
