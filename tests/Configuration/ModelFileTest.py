#!/usr/bin/env python
# Shine.Configuration.ModelFile test suite
# Written by A. Degremont 2009-10-02
# $Id$


"""Unit test for ModelFile"""

import os
import sys
import unittest

sys.path.insert(0, '../lib')

from TestUtils import makeTestFile, makeTempFilename
from Shine.Configuration.ModelFile import *


class ModelFileTest(unittest.TestCase):

    def makeTestModel(self, text):
        """
        Create a temporary file instance and returns a ModelFile with it.
        """
        f = makeTestFile(text)
        model = ModelFile(filename=f.name)
        return model

    def testSyntaxComments(self):
        """test comment syntax"""

        model = self.makeTestModel("""

# Comments
   # Some comments with spaces
       # Some with tabs and ponctuation: toto= value
""")

        self.assertEqual(len(model.keys), 0)

    def testBasic(self):
        """test a basic key/value definition"""

        model = self.makeTestModel("\nfoo: bar\n\n")

        self.assertEqual(model.has_key('foo'), True)
        self.assertEqual(model.get('foo'), ['bar'])

    def testMultipleValues(self):
        """test multiple values for the same key"""

        model = self.makeTestModel("""
# Keys
multiple: value1
multiple: value2
""")

        self.assertEqual(model.has_key('multiple'), True)
        self.assertEqual(model.get('multiple'), ['value1', 'value2'])

    def testEmptyValue(self):
        """test empty value"""

        model = self.makeTestModel("key : \n")

        self.assertEqual(model.has_key('key'), True)
        self.assertEqual(model.get('key'), [''])

    def testTabs(self):
        """test with various tabs"""

        model = self.makeTestModel("""
# Tabs
        key_tabbed: value2
        key_tabbed2:    value_tabbed
""")

        self.assertEqual(model.has_key('key_tabbed'), True)
        self.assertEqual(model.get('key_tabbed'), ['value2'])

        self.assertEqual(model.has_key('key_tabbed2'), True)
        self.assertEqual(model.get('key_tabbed2'), ['value_tabbed'])

    def testWrongSyntax(self):
        """test different invalid syntax"""

        f = makeTestFile("wrong syntax line\n")
        self.assertRaises(ModelFileSyntaxError, ModelFile, filename=f.name)

    def testNewAndLoad(self):
        """test instanciate and load"""

        m = ModelFile()
        self.failIf(m.filename)

        # Load one file
        f1 = makeTestFile("""
key: value
key2: value
key3: value
key4:
key4: again
key4: re-again
""")
        m.load_from_file(f1.name)
        self.assertEqual(len(m.keys.keys()), 4)
        self.assertEqual(m.get_filename(), f1.name)

        # Load another file now
        f2 = makeTestFile("""
key: value
key2: value
key3: value
key4:
key5: again
key6: re-again
""")
        m.load_from_file(f2.name)
        self.assertEqual(len(m.keys.keys()), 6)
        self.assertEqual(m.get_filename(), f2.name)

    def testAddSave(self):
        """test to save a model file"""
        m1 = ModelFile()
        m1.add('key1', 'value')
        m1.add('key2', 'value')
        m1.add('key3', 'value')
        m1.add('key3', 'value')

        # Get a temporary name for a file
        filename = makeTempFilename()

        # First, the ModelFile should not have its name defined
        self.failIf(m1.get_filename())

        # Save it
        m1.save_to_file(filename=filename)
        # Name should be defined
        self.assertEqual(m1.get_filename(), filename)

        # Now, read the file created, it should be the same
        m2 = ModelFile(filename=filename)
        self.assertEqual(m2.get_filename(), filename)
        self.assertEqual(len(m1.keys.keys()), len(m2.keys.keys()))
	
        # Clean the file
        os.unlink(filename)


    def testDefaults(self):
        """test correct default value usage"""

        class MyModelFile(ModelFile):
            syntax   = { 'key1': ['value1','value2'],
                         'key2': 'string',
                       }
            defaults = { 'key1': 'value2',
                         'key2': [ 'value' ]
                       } 

        m = MyModelFile()
        # get()
        self.assertEqual(m.get('key1'), ['value2'])
        self.assertNotEqual(m.get('key1'), 'value2')
        self.assertRaises(KeyError, m.get, 'invalid_key')
        # get_one()
        self.assertEqual(m.get_one('key1'), 'value2')
        self.assertEqual(m.get_one('key2'), 'value')


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ModelFileTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
