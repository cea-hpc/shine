#!/usr/bin/env python
# Shine.Configuration.Model test suite
# Written by A. Degremont 2009-07-16
# $Id$


"""Unit test for Model"""

import sys
import unittest

sys.path.insert(0, '../lib')

from TestUtils import makeTestFile
from Shine.Configuration.Model import Model

class ModelTest(unittest.TestCase):

    def makeTestModel(self, text):
        """
        Create a temporary file instance and returns a ModelFile with it.
        """
        f = makeTestFile(text)
        model = Model(filename=f.name)
        return model

    def testDefaultValues(self):
        """test defaults values"""
        # All default values had been declared in syntax dict.
        syntax_keys = set(Model.syntax.keys())
        defaults_keys = set(Model.defaults.keys())
        self.assertTrue(defaults_keys <= syntax_keys)

        m = Model()
        self.assertEqual(m.get('stripe_size'), [ 1048576 ])
        self.assertEqual(m.get('stripe_count'), [ 1 ])
        self.assertEqual(m.get('quota_type'), ['ug'])

    def testLoadExample(self):
        """Load example.lmf and checks it."""
        m = Model()
        m.load_from_file("../conf/models/example.lmf")
        self.assertEqual(len(m.keys.keys()), 19)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ModelTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
