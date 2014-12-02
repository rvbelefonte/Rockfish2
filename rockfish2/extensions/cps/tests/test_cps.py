"""
Test suite for the cps.cps module
"""
import os
import doctest
import unittest
import datetime
import numpy as np
import matplotlib.pyplot as plt
from rockfish2.utils.loaders import get_example_file
from rockfish2.extensions.cps import cps

class cpsTestCase(unittest.TestCase):
    """
    Tests for the cps.model module
    """
    def test_init_empty(self):
        """
        Should initialize a CPSModel instance with an empty model
        """
        with cps.CPS() as m:

            self.assertEqual(len(m.model), 0)
            self.assertTrue(hasattr(m, 'write'))

    def test_sprep96(self):
        """
        Should run sprep96 for the current model
        """
        with cps.CPS() as m:
            m.read(get_example_file('nmodel.wat'))
            m.sprep96()

            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'model.dat')))
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'sdisp96.dat')))

    def test_sdisp96(self):
        """
        Should run sdisp96 for the current model
        """
        with cps.CPS() as m:
            m.read(get_example_file('nmodel.wat'))
            m.sprep96()
            m.sdisp96()

    def test_scomb96(self):
        """
        Should run scomb96 for the current model
        """
        with cps.CPS(cleanup=False) as m:
            m.read(get_example_file('lmodel.d'))
            m.sprep96()
            m.sdisp96()
            m.scomb96(L=True, rename=True)
            m.scomb96(R=True, rename=True, XMIN=3.9, XMAX=4.0,
                    CMIN=4.3, CMAX=4.7)

            self.assertFalse(os.path.isfile(os.path.join(m.DIR,
                'tsdisp96.ray')))
            self.assertFalse(os.path.isfile(os.path.join(m.DIR,
                'tsdisp96.lov')))
            
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'sdisp96.ray')))
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'sdisp96.lov')))


    def test_sregn96(self):
        """
        Should run sregn96 for the current model
        """
        with cps.CPS() as m:
            m.read(get_example_file('nmodel.wat'))
            m.sprep96()
            m.sdisp96()
            m.sregn96()

    def test_sdpder96(self):
        """
        Should run sdpder96 for the current model
        """
        with cps.CPS() as m:
            m.read(get_example_file('nmodel.wat'))
            m.sprep96(L=True, R=True)
            m.sdisp96()
            m.sregn96(hs=0, hr=0, der=True)
            m.slegn96(hs=0, hr=0, der=True)
            m.sdpder96(L=True, txt=True)
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'SLDER.TXT')))
            m.sdpder96(R=True, txt=True)
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'SRDER.TXT')))

    def test_sdpegn96(self):
        """
        Should run sdpegn96
        """
        with cps.CPS() as m:
            m.read(get_example_file('nmodel.wat'))
            m.sprep96(L=True, R=True)
            m.sdisp96()
            m.sregn96(hs=0, hr=0, der=True)
            m.slegn96(hs=0, hr=0, der=True)
            m.sdpder96(L=True, C=True, txt=True)
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'SLDER.TXT')))
            m.sdpder96(R=True, C=True, txt=True)
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'SRDER.TXT')))

    def test_plot_der(self):
        """
        Should calculate depth-dependent functions
        """
        with cps.CPS(cleanup=True) as m:
            m.read(get_example_file('nmodel.wat'))
            
            mod, der = m.plot_der(hr=20, hs=10, dt=0.1, npts=2, nmod=1,
                    interp=True)
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'SLDER.TXT')))
            self.assertTrue(os.path.isfile(os.path.join(m.DIR,
                'SRDER.TXT')))

            mod.plot()
            
    def test_plot_dispersion(self):
        """
        Should calculate dispersion
        """
        # should reproduce example on pages 61 and 62 of CPS manual
        with cps.CPS(cleanup=True) as m:
            m.read(get_example_file('model.d'))

            disp = m.plot_dispersion(hr=0, hs=10, npts=1026, 
                    fmax=4, nmod=100, group=False)
            
        # should reproduce example on page 65 of CPS manual
        with cps.CPS(cleanup=True) as m:
            m.read(get_example_file('nmodel.wat'))

            disp = m.plot_dispersion(hr=10, hs=20, npts=4098, 
                    fmax=50, nmod=1, group=False, period=True,
                    semilogx=True, xlim=(4, 500), ylim=(2.5, 5))

    def test_plot_dispersion_repair(self):
        """
        Should calculate dispersion
        """
        # should reproduce example on pages 70 and 71 of CPS manual

        # as is
        with cps.CPS(cleanup=True) as m:
            m.read(get_example_file('lmodel.d'))

            disp = m.plot_dispersion(hr=0, hs=0, npts=1026, 
                    fmax=4, nmod=400, group=False)

        # with repair
        with cps.CPS(cleanup=False) as m:
            m.read(get_example_file('lmodel.d'))

            repairs = [{'R': True, 'XMIN': 3.9, 'XMAX': 4.0,
                'CMIN': 4.3, 'CMAX': 4.7},
                {'R': True, 'I': True, 'XMIN': 1.75, 'XMAX': 1.85,
                'CMIN': 4.1, 'CMAX': 4.2}]

            disp = m.plot_dispersion(hr=0, hs=0, npts=1026, 
                    fmax=4, nmod=400, group=False, repairs=repairs)

    def dev_plot_disp_depth(self):

        fig = plt.figure()
        ax = fig.add_subplot(111)

        depths = [0, 5, 8]
        clrs = ['c', 'm', 'r']
        for c, h in zip(clrs, depths):

            with cps.CPS(cleanup=False) as m:

                m.read(get_example_file('nmodel.wat'))

                disp = m.plot_disp(ax=ax, hr=h, hs=h, npts=128,
                        fmax=5, nmod=1, group=True, rayleigh_color=c,
                        love_color=c)
        plt.show()
            

def suite():
    testSuite = unittest.makeSuite(cpsTestCase, 'dev')
    #XXX testSuite.addTest(doctest.DocTestSuite(database))

    return testSuite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

