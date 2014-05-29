#!/usr/bin/env python
# Shine.Configuration.Model test suite
# Copyright (C) 2009-2014 CEA


"""Unit test for Model"""

import unittest
import time

from Utils import makeTempFile

from Shine.Configuration.NidMap import NidMap
from Shine.Configuration.Model import Model, ModelFileValueError

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
        self.assertEqual(len(m), 19)

    def testTooLongFSName(self):
        """Model with a too long fsname"""
        testfile = makeTempFile("""fs_name: too_long_name""")
        model = Model()
        self.assertRaises(ModelFileValueError, model.load, testfile.name)

    def testHaNodes(self):
        """Model with several ha_nodes."""
        model = self.makeTempModel("""fs_name: ha_node
mgt: node=foo1 dev=/dev/sda ha_node=foo2 ha_node=foo3""")
        self.assertEqual(model.get('mgt')[0].get('ha_node'), ['foo2', 'foo3'])

    def test_unbalanced_nid_map(self):
        """Model with nid_map with several ranges."""
        model = self.makeTempModel("""fs_name: nids
nid_map: nodes=foo[1-2],bar[1-9] nids=foo[1-2],bar[1-9]@tcp""")
        self.assertEqual(len(model.elements('nid_map')), 1)
        self.assertEqual(model.elements('nid_map')[0].as_dict(),
             { 'nodes': 'foo[1-2],bar[1-9]', 'nids': 'foo[1-2],bar[1-9]@tcp' })

    def test_big_nid_map_scalable(self):
        """check big nid mapping is scalable."""
        model = Model()
        model.parse("nid_map: nodes=foo[1-9999] nids=bar[1-9999]@tcp")
        before = time.time()
        NidMap.fromlist(model.get('nid_map'))
        self.assertTrue(time.time() - before < .5)

    def testSeveralNidMap(self):
        """Model with several nid_map lines."""
        model = self.makeTempModel("""fs_name: nids
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp
nid_map: nodes=foo[7] nids=foo[7]@tcp""")
        self.assertEqual(len(model.elements('nid_map')), 2)
        self.assertEqual(model.elements('nid_map')[0].as_dict(),
                { 'nodes': 'foo[1-2]', 'nids': 'foo[1-2]@tcp' })
        self.assertEqual(model.elements('nid_map')[1].as_dict(),
                { 'nodes': 'foo[7]', 'nids': 'foo[7]@tcp' })

    def test_match_device_ignore_index(self):
        """test match_device() does not try to match index property"""
        model = Model()
        model.parse("""fs_name: nids
nid_map: nodes=foo[7] nids=foo[7]@tcp
ost: node=foo7 index=0""")
        candidate = [ {'node': 'foo7', 'dev': '/dev/sda'} ]
        matched = model.get('ost')[0].match_device(candidate)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].get('dev'), '/dev/sda')

    def test_match_device_error(self):
        model = Model()
        model.parse("""fs_name: nids
nid_map: nodes=foo[7] nids=foo[7]@tcp
mgt: node=(\<badregexp>""")
        candidate = [ {'node': 'foo7', 'dev': '/dev/sda'} ]
        self.assertRaises(ModelFileValueError, model.get('mgt')[0].match_device,
                candidate)

    def test_match_device_missing_prop(self):
        """check missing property does not match in match_device()"""
        model = Model()
        model.parse("""fs_name: nids
nid_map: nodes=foo[7] nids=foo[7]@tcp
mgt: node=foo7 network=tcp""")
        candidate = [ {'node': 'foo7', 'dev': '/dev/sda'} ]
        self.assertEqual(len(model.get('mgt')[0].match_device(candidate)), 0)

    def test_several_spaces(self):
        model = Model()
        model.parse("""fs_name:  spaces 
nid_map:  nodes=foo[7]  nids=foo[7]@tcp
mgt:  node=foo7 """)
        self.assertEqual(model.get('fs_name'), 'spaces')
        self.assertEqual(len(model.elements('nid_map')), 1)
        self.assertEqual(model.elements('nid_map')[0].as_dict(),
                { 'nodes': 'foo[7]', 'nids': 'foo[7]@tcp' })

    def test_diff_ost(self):
        """check diff detects updated targets."""
        model = Model()
        model.parse("""fs_name: diff
nid_map: nodes=foo1 nids=foo1@tcp
ost: node=foo1 dev=/dev/sda
ost: node=foo1 dev=/dev/sdc mode=external """)

        new_m = Model()
        new_m.parse("""fs_name: diff
nid_map: nodes=foo1 nids=foo1@tcp
ost: node=foo1 dev=/dev/sdc jdev=/dev/sdd """)

        added, changed, removed = model.diff(new_m)
        self.assertEqual(len(added), 0)
        self.assertEqual(str(removed), "ost:node=foo1 dev=/dev/sda")
        self.assertEqual(str(changed),
                                    "ost:node=foo1 dev=/dev/sdc jdev=/dev/sdd")

    def test_diff_client(self):
        """check diff detects updated clients."""
        model = Model()
        model.parse("""fs_name: diff
nid_map: nodes=foo1 nids=foo1@tcp
client: node=foo1""")

        new_m = Model()
        new_m.parse("""fs_name: diff
nid_map: nodes=foo1 nids=foo1@tcp
client: node=foo1 mount_options=ro""")

        added, changed, removed = model.diff(new_m)
        self.assertEqual(len(added), 0)
        self.assertEqual(len(removed), 0)
        self.assertEqual(str(changed), "client:node=foo1 mount_options=ro")
