"""
Master test suite for the Rockfish2 library
"""
import unittest

loader = unittest.TestLoader()
tests = loader.discover('rockfish2')
testRunner = unittest.runner.TextTestRunner()

if __name__ == "__main__":

    testRunner.run(tests)
