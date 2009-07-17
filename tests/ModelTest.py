#!/usr/bin/env python
# Shine.Configuration.Model test suite
# Written by A. Degremont 2009-07-16
# $Id$


"""Unit test for Model"""

import sys
import unittest
import tempfile

sys.path.insert(0, '../lib')

from Shine.Configuration.Model import Model

class ModelTest(unittest.TestCase):

    def makeTestFile(self, text):
        """
        Create a temporary file with the provided text.
        """
        f = tempfile.NamedTemporaryFile()
        f.write(text)
        f.flush()
        return f

    def makeTestModel(self, text):
        """
        Create a temporary file instance and returns a ModelFile with it.
        """
        f = self.makeTestFile(text)
        model = Model(filename=f.name)
        return model

    def testLoadExample(self):
        """Load example.lmf and checks it."""
        m = Model()
        m.load_from_file("../conf/models/example.lmf")
        self.assertEqual(len(m.get_keys()), 20)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ModelTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
