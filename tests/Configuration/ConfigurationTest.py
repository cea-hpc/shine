#!/usr/bin/env python
# Shine.Configuration.Configuration test suite
# Written by A. Degremont 2010-11-21
# $Id$


"""Unit test for Configuration"""

import unittest

from Utils import setup_tempdirs, clean_tempdirs, makeTempFile
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Exceptions import ConfigException

class ConfigurationTest(unittest.TestCase):

    def setUp(self):
        self._conf = None
        setup_tempdirs()

    def tearDown(self):
        if self._conf:
            self._conf.unregister_fs()
        clean_tempdirs()

    def make_config(self, text):
        """
        Create a temporary file instance and returns a Configuration with it.
        """
        self._testfile = makeTempFile(text)
        conf = Configuration.create_from_model(self._testfile.name)
        return conf

    def test_accessors(self):
        """Configuration get_* accessors."""
        self._conf = Configuration.create_from_model("../conf/models/example.lmf")
        self.assertEqual(self._conf.get_stripecount(), 1)
        self.assertEqual(self._conf.get_stripesize(), 1048576)
        self.assertTrue(self._conf.get_cfg_filename())

    def test_get_client_nodes_empty(self):
        """Configuration get_client_nodes (no clients)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
        """)
        self.assertEqual(len(self._conf.get_client_nodes()), 0)

    def test_get_client_nodes_empty(self):
        """Configuration get_client_nodes (some clients)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
client: node=foo[1-3]
client: node=foo[5-7]
        """)
        self.assertEqual(str(self._conf.get_client_nodes()), "foo[1-3,5-7]")

    def test_empty_get_client_mounts(self):
        """Configuration get_client_mounts (no clients)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
        """)

        # Simplest conf, using global mount_path
        mountpaths = self._conf.get_client_mounts()
        self.assertEqual(len(mountpaths), 0)

    def test_simple_get_client_mounts(self):
        """Configuration get_client_mounts (global)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
mount_path: /foo
client: node=foo[2-3]
        """)

        # Simplest conf, using global mount_path
        mountpaths = self._conf.get_client_mounts()
        self.assertEqual(len(mountpaths), 1)
        self.assertEqual(str(mountpaths['/foo']), 'foo[2-3]')

    def test_several_get_client_mounts(self):
        """Configuration get_client_mounts (several)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
mount_path: /foo
client: node=foo[2-3]
client: node=foo[3-5] mount_path=/foo2
        """)

        mountpaths = self._conf.get_client_mounts()
        self.assertEqual(len(mountpaths), 2)
        self.assertEqual(str(mountpaths['/foo']), 'foo[2-3]')
        self.assertEqual(str(mountpaths['/foo2']), 'foo[3-5]')

    def test_specific_get_client_mounts(self):
        """Configuration get_client_mounts (no global)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
client: node=foo[2-3] mount_path=/foo1
client: node=foo[3-5] mount_path=/foo2
        """)

        mountpaths = self._conf.get_client_mounts()
        self.assertEqual(len(mountpaths), 2)
        self.assertEqual(str(mountpaths['/foo1']), 'foo[2-3]')
        self.assertEqual(str(mountpaths['/foo2']), 'foo[3-5]')

    def test_missing_get_client_mounts(self):
        """Configuration get_client_mounts (missing path)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
client: node=foo[2-3]
client: node=foo[3-5] mount_path=/foo2
        """)
        self.assertRaises(ConfigException, self._conf.get_client_mounts)

    def test_has_quota_old_style(self):
        """Configuration has_quota (old style)"""

        # Old style quota mode value is 'yes' or 'no'
        self._conf = self.make_config("""
fs_name: hasquota
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
quota: no
client: node=foo[2-3]
        """)
        self.assertFalse(self._conf.has_quota())

        self._conf = self.make_config("""
fs_name: hasquota
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
quota: yes
client: node=foo[2-3]
        """)
        self.assertTrue(self._conf.has_quota())

    def test_has_quota_new_style(self):
        """Configuration has_quota (new style)"""

        # New style quota mode value is 'True' or 'False'
        self._conf = self.make_config("""
fs_name: hasquota
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
quota: False
client: node=foo[2-3]
        """)
        self.assertFalse(self._conf.has_quota())

        self._conf = self.make_config("""
fs_name: hasquota
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
quota: True
client: node=foo[2-3]
        """)
        self.assertTrue(self._conf.has_quota())
