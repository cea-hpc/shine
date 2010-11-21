#!/usr/bin/env python
# Shine.Configuration.Model test suite
# Written by A. Degremont 2009-07-16
# $Id$


"""Unit test for Model"""

import unittest

from Utils import makeTempFile
from Shine.Configuration.Model import Model

class ModelTest(unittest.TestCase):

    def makeTempModel(self, txt):
        """helper method for creating a temp file and loading it as Model"""
        self._testfile = makeTempFile(txt)
        model = Model()
        model.load(self._testfile.name)
        return model

    def testDefaultValues(self):
        """test defaults values"""
        m = Model()
        self.assertEqual(m.get('stripe_size'), 1048576)
        self.assertEqual(m.get('stripe_count'), 1)
        self.assertEqual(m.get('quota_type'), 'ug')

    def testLoadExample(self):
        """Load example.lmf and checks it."""
        m = Model()
        m.load('../conf/models/example.lmf')
        self.assertEqual(len(m), 20)

    def testTooLongFSName(self):
        """Model with a too long fsname"""
        testfile = makeTempFile("""fs_name: too_long_name""")
        model = Model()
        self.assertRaises(ValueError, model.load, testfile.name)

    def testHaNodes(self):
        """Model with several ha_nodes."""
        model = self.makeTempModel("""fs_name: ha_node
mgt: node=foo1 dev=/dev/sda ha_node=foo2 ha_node=foo3""")
        self.assertEqual(model.get('mgt')[0].get('ha_node'), ['foo2', 'foo3'])

    def testSeveralNidMap(self):
        """Model with several nid_map lines."""
        model = self.makeTempModel("""fs_name: nids
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp
nid_map: nodes=foo[7] nids=foo[7]@tcp""")
        self.assertEqual(len(model.elements('nid_map')), 3)
        self.assertEqual(model.elements('nid_map')[0].as_dict(),
                { 'nodes': 'foo1', 'nids': 'foo1@tcp' })
        self.assertEqual(model.elements('nid_map')[1].as_dict(),
                { 'nodes': 'foo2', 'nids': 'foo2@tcp' })
        self.assertEqual(model.elements('nid_map')[2].as_dict(),
                { 'nodes': 'foo7', 'nids': 'foo7@tcp' })

    def testMatchDevice(self):
        model = self.makeTempModel("""fs_name: nids
nid_map: nodes=foo[7] nids=foo[7]@tcp
mgt: node=foo7""")
        candidate = [ {'node': 'foo7', 'dev': '/dev/sda'} ]
        matched = model.get('mgt')[0].match_device(candidate)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].get('dev'), '/dev/sda')

    def testMatchDeviceError(self):
        model = self.makeTempModel("""fs_name: nids
nid_map: nodes=foo[7] nids=foo[7]@tcp
mgt: node=(\<badregexp>""")
        candidate = [ {'node': 'foo7', 'dev': '/dev/sda'} ]
        self.assertRaises(ValueError, model.get('mgt')[0].match_device,
                candidate)
