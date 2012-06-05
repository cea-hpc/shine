#!/usr/bin/env python
# Shine.Configuration.Backend.File test suite
# Written by A. Degremont 2010-11-20
# $Id$


"""Unit test for Backend File"""

import unittest

from Utils import makeTempFile, setup_tempdirs, clean_tempdirs
from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

class BackendFileTest(unittest.TestCase):

    def setUp(self):
        self._conf = None
        setup_tempdirs()
        Globals().replace('backend', 'File')

    def tearDown(self):
        Globals().replace('storage_file', '/etc/shine/storage.conf')
        if self._conf is not None:
            self._conf.unregister_fs()
        clean_tempdirs()
        Globals().replace('backend', 'None')

    def make_temp_conf(self, txt):
        self._storagefile = makeTempFile(txt)
        Globals().replace('storage_file', self._storagefile.name)

    def make_temp_fs(self, txt):
        self._fsfile = makeTempFile(txt)
        self._conf = Configuration.create_from_model(self._fsfile.name)
        self._model = self._conf._fs.model

    def test_simple_mgs(self):
        self.make_temp_conf("mgt: node=foo1 dev=/dev/sda")
        self.make_temp_fs("""fs_name: example
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp0
mgt: node=foo1""")
        self.assertEqual(self._model.get('mgt')[0].get('dev'), '/dev/sda')

    def test_ha_node(self):
        """target with ha_node"""
        self.make_temp_conf("mgt: node=foo1 dev=/dev/sda ha_node=foo1")
        self.make_temp_fs("""fs_name: example
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp0
mgt: node=foo1""")
        self.assertEqual(self._model.get('mgt')[0].get('ha_node'), ['foo1'])

    def test_ha_nodes(self):
        """target with several ha_nodes"""
        self.make_temp_conf("mgt: node=foo1 dev=/dev/sda ha_node=foo1 ha_node=foo2")
        self.make_temp_fs("""fs_name: example
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp0
mgt: node=foo1 ha_node=foo1""")
        self.assertEqual(self._model.get('mgt')[0].get('ha_node'), ['foo1', 'foo2'])

    def test_multiple_matches(self):
        self.make_temp_conf(
"""mgt: node=foo1 dev=/dev/sda
mdt: node=foo1 dev=/dev/sdd
ost: node=foo1 dev=/dev/sdb
ost: node=foo1 dev=/dev/sdc
ost: node=foo2 dev=/dev/sdb""")
        self.make_temp_fs("""fs_name: example
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp0
mgt: node=foo1
mdt: node=foo1
ost: node=foo1""")
        self.assertEqual(self._model.get('mgt')[0].get('dev'), '/dev/sda')
        self.assertEqual(self._model.get('mdt')[0].get('dev'), '/dev/sdd')
        self.assertEqual(len(self._model.elements('ost')), 2)
        self.assertEqual(self._model.get('ost')[0].get('dev'), '/dev/sdb')
        self.assertEqual(self._model.get('ost')[1].get('dev'), '/dev/sdc')

    def test_index_external(self):
        self.make_temp_conf(
"""mgt: node=foo1 dev=/dev/sda
mdt: node=foo1 dev=/dev/sdd
ost: node=foo1 dev=/dev/sdb
ost: node=foo1 dev=/dev/sdc
ost: node=foo2 dev=/dev/sdb""")
        self.make_temp_fs("""fs_name: example
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp0
mgt: node=foo1
mdt: node=foo1 mode=external
ost: node=foo2
ost: node=foo1 dev=/dev/sdb index=0
ost: node=foo1 dev=/dev/sdc""")
        self.assertEqual(self._model.get('mgt')[0].get('dev'), '/dev/sda')
        self.assertEqual(self._model.get('mdt')[0].get('mode'), 'external')
        self.assertEqual(len(self._model.elements('ost')), 3)
        self.assertEqual(self._model.get('ost')[0].get('dev'), '/dev/sdb')
        self.assertEqual(self._model.get('ost')[0].get('index'), 1)
        self.assertEqual(self._model.get('ost')[1].get('dev'), '/dev/sdb')
        self.assertEqual(self._model.get('ost')[1].get('index'), 0)
        self.assertEqual(self._model.get('ost')[2].get('dev'), '/dev/sdc')
        self.assertEqual(self._model.get('ost')[2].get('index'), 2)
