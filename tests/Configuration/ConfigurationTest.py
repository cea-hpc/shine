#!/usr/bin/env python
# Shine.Configuration.Configuration test suite
# Written by A. Degremont 2010-11-21


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

    def test_empty_iter_clients(self):
        """Configuration iter_clients (no clients)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
        """)

        # Simplest conf, using global mount_path
        mountpaths = list(self._conf.iter_clients())
        self.assertEqual(len(mountpaths), 0)

    def test_simple_iter_clients(self):
        """Configuration iter_clients (global)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
mount_path: /foo
client: node=foo[2-3]
        """)

        # Simplest conf, using global mount_path
        mountpaths = list(self._conf.iter_clients())
        self.assertEqual(len(mountpaths), 2)
        self.assertEqual(mountpaths[0], ('foo2', '/foo', None))
        self.assertEqual(mountpaths[1], ('foo3', '/foo', None))

    def test_simple_iter_clients_options(self):
        """Configuration iter_clients (global options)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
mount_path: /foo
mount_options: acl
client: node=foo[2-3]
        """)

        # Simplest conf, using global mount_path
        mountpaths = list(self._conf.iter_clients())
        self.assertEqual(len(mountpaths), 2)
        self.assertEqual(mountpaths[0], ('foo2', '/foo', 'acl'))
        self.assertEqual(mountpaths[1], ('foo3', '/foo', 'acl'))

    def test_several_iter_clients(self):
        """Configuration iter_clients (several)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
mount_path: /foo
client: node=foo[2-3]
client: node=foo[3-5] mount_path=/foo2
        """)

        mountpaths = list(self._conf.iter_clients())
        self.assertEqual(len(mountpaths), 5)
        self.assertEqual(mountpaths[0], ('foo2', '/foo', None))
        self.assertEqual(mountpaths[1], ('foo3', '/foo', None))
        self.assertEqual(mountpaths[2], ('foo3', '/foo2', None))
        self.assertEqual(mountpaths[3], ('foo4', '/foo2', None))
        self.assertEqual(mountpaths[4], ('foo5', '/foo2', None))

    def test_several_iter_clients_options(self):
        """Configuration iter_clients (several options)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
mount_path: /foo
mount_options: acl
client: node=foo[2-3]
client: node=foo[3-5] mount_path=/foo2 mount_options=noatime
        """)

        mountpaths = list(self._conf.iter_clients())
        self.assertEqual(len(mountpaths), 5)
        self.assertEqual(mountpaths[0], ('foo2', '/foo', 'acl'))
        self.assertEqual(mountpaths[1], ('foo3', '/foo', 'acl'))
        self.assertEqual(mountpaths[2], ('foo3', '/foo2', 'noatime'))
        self.assertEqual(mountpaths[3], ('foo4', '/foo2', 'noatime'))
        self.assertEqual(mountpaths[4], ('foo5', '/foo2', 'noatime'))

    def test_specific_iter_clients(self):
        """Configuration iter_clients (no global)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
client: node=foo[2-3] mount_path=/foo1
client: node=foo[3-5] mount_path=/foo2
        """)

        mountpaths = list(self._conf.iter_clients())
        self.assertEqual(len(mountpaths), 5)
        self.assertEqual(mountpaths[0], ('foo2', '/foo1', None))
        self.assertEqual(mountpaths[1], ('foo3', '/foo1', None))
        self.assertEqual(mountpaths[2], ('foo3', '/foo2', None))
        self.assertEqual(mountpaths[3], ('foo4', '/foo2', None))
        self.assertEqual(mountpaths[4], ('foo5', '/foo2', None))

    def test_specific_iter_clients_options(self):
        """Configuration iter_clients (no global mount_options)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
mount_path: /foo
client: node=foo[2-3] mount_options=acl,noatime
client: node=foo[4-5]
        """)

        mountpaths = list(self._conf.iter_clients())
        self.assertEqual(len(mountpaths), 4)
        self.assertEqual(mountpaths[0], ('foo2', '/foo', 'acl,noatime'))
        self.assertEqual(mountpaths[1], ('foo3', '/foo', 'acl,noatime'))
        self.assertEqual(mountpaths[2], ('foo4', '/foo', None))
        self.assertEqual(mountpaths[3], ('foo5', '/foo', None))

    def test_missing_iter_clients(self):
        """Configuration iter_clients (missing path)"""
        self._conf = self.make_config("""
fs_name: climount
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: mode=external
client: node=foo[2-3]
client: node=foo[3-5] mount_path=/foo2
        """)
        def listclients():
            list(self._conf.iter_clients())
        self.assertRaises(ConfigException, listclients)

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
