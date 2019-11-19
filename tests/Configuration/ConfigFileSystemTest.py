#!/usr/bin/env python
# Shine.Configuration.FileSystem class
# Copyright (C) 2009-2017 CEA


"""Unit test for Shine.Configuration.FileSystem"""

import unittest
import textwrap
import time

from Utils import makeTempFile, setup_tempdirs, clean_tempdirs
from Shine.Configuration.FileSystem import FileSystem, ModelFileIOError, ConfigDeviceNotFoundError
from Shine.Configuration.Exceptions import ConfigException, ConfigInvalidFileSystem
from Shine.Configuration.TargetDevice import TargetDevice
from Shine.Configuration.Backend.Backend import Backend

class FileSystemTest(unittest.TestCase):

    def setUp(self):
        self._fs = None
        self._testfile = None
        setup_tempdirs()

    def tearDown(self):
        # Remove file from cache
        if self._fs:
            self._fs.unregister()
        # Delete the temp cache directory
        clean_tempdirs()

    def makeConfFileSystem(self, text):
        """
        Create a temporary file instance and returns a FileSystem with it.
        """
        self._testfile = makeTempFile(text)
        fsconf = FileSystem.create_from_model(self._testfile.name)
        return fsconf

    def testLoadFile(self):
        """create a FileSystem from model example.lmf"""
        fs = FileSystem(filename="../conf/models/example.lmf")
        self.assertEqual(len(fs.model), 15)

    def test_missing_config_file(self):
        """test missing config file detection"""
        self.assertRaises(ModelFileIOError, FileSystem, filename="/bad/file")

    def testMGSOnly(self):
        """filesystem with only a MGS"""
        self._fs = self.makeConfFileSystem("""
fs_name: mgs
nid_map: nodes=foo1 nids=foo1@tcp
mgt: node=foo1 dev=/dev/dummy
""")
        self.assertEqual(len(self._fs.model), 3)

    def testRouterOnly(self):
        """filesystem with only routers"""
        self._fs = self.makeConfFileSystem("""
fs_name: router
nid_map: nodes=foo1 nids=foo1@tcp
router: node=foo1
""")
        self.assertEqual(len(self._fs.model), 3)

    def testClientOnly(self):
        """filesystem with only clients"""
        self._fs = self.makeConfFileSystem("""
fs_name: clients
nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp
mgt: node=foo1 dev=/dev/dummy
client: node=foo[2-3]
""")
        self.assertEqual(len(self._fs.model), 4)

    def testMDTnoMGT(self):
        """filesystem with a MDT and no MGT"""
        self.assertRaises(ConfigInvalidFileSystem, self.makeConfFileSystem, """
fs_name: mdtnomgt
nid_map: nodes=foo1 nids=foo1@tcp
mdt: node=foo1 dev=/dev/dummy
""")

    def testOSTnoMGT(self):
        """filesystem with OSTs and no MGT"""
        self.assertRaises(ConfigInvalidFileSystem, self.makeConfFileSystem, """
fs_name: ostnomgt
nid_map: nodes=foo[1,2] nids=foo[1,2]@tcp
ost: node=foo1 dev=/dev/dummy
ost: node=foo2 dev=/dev/dummy
""")

    def testMGTandMDTnoOST(self):
        """filesystem with both MGT and MDT and no OST"""
        self.assertRaises(ConfigInvalidFileSystem, self.makeConfFileSystem, """
fs_name: example
nid_map: nodes=foo1 nids=foo1@tcp
mgt: node=foo1 dev=/dev/dummy2
mdt: node=foo1 dev=/dev/dummy1
""")

    def testMultipleNidMap(self):
        """filesystem with complex nid setup"""
        self._fs = self.makeConfFileSystem("""
fs_name: example
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp0
nid_map: nodes=foo[1-2] nids=foo[1-2]-bone@tcp1
mgt: node=foo1 ha_node=foo2
""")
        self.assertEqual(len(self._fs.model), 3)
        self.assertEqual(self._fs.get_nid('foo1'), ['foo1@tcp0', 'foo1-bone@tcp1'])
        self.assertEqual(self._fs.get_nid('foo2'), ['foo2@tcp0', 'foo2-bone@tcp1'])

    def test_unbalanced_nid_map(self):
        """filesystem with nids with several ranges."""
        self._fs = self.makeConfFileSystem("""
fs_name: nids
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp
nid_map: nodes=bar[1-3] nids=bar[1-3]@tcp
""")
        self.assertEqual(self._fs.get_nid('foo1'), ['foo1@tcp'])
        self.assertEqual(self._fs.get_nid('foo2'), ['foo2@tcp'])
        self.assertEqual(self._fs.get_nid('bar1'), ['bar1@tcp'])
        self.assertEqual(self._fs.get_nid('bar2'), ['bar2@tcp'])
        self.assertEqual(self._fs.get_nid('bar3'), ['bar3@tcp'])

    def test_big_nid_map_scalable(self):
        """filesystem with nids with several ranges."""
        before = time.time()
        self._fs = self.makeConfFileSystem("""
fs_name: nids
nid_map: nodes=foo[1-9999] nids=bar[1-9999]@tcp
""")
        elapsed = time.time() - before
        self.assertTrue(elapsed < 2, "%.2fs exceeds 2s threshold" % elapsed)
        self.assertEqual(len(self._fs.nid_map), 9999)

    def testNoIndexDefined(self):
        """filesystem with no index set"""
        self._fs = self.makeConfFileSystem("""
fs_name: example
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp0
mgt: node=foo1
mdt: node=foo2
ost: node=foo2
ost: node=foo1
""")
        self.assertEqual(len(self._fs.get('ost')), 2)
        self.assertEqual(self._fs.get('ost')[0].get('node'), 'foo2')
        self.assertEqual(self._fs.get('ost')[0].get('index'), 0)
        self.assertEqual(self._fs.get('ost')[1].get('node'), 'foo1')
        self.assertEqual(self._fs.get('ost')[1].get('index'), 1)

    def testSomeIndexedDefined(self):
        """filesystem with not all indexes set"""
        self._fs = self.makeConfFileSystem("""
fs_name: example
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp0
mgt: node=foo1
mdt: node=foo2
ost: node=foo2
ost: node=foo1 index=0
""")
        self.assertEqual(len(self._fs.get('ost')), 2)
        self.assertEqual(self._fs.get('ost')[0].get('node'), 'foo2')
        self.assertEqual(self._fs.get('ost')[0].get('index'), 1)
        self.assertEqual(self._fs.get('ost')[1].get('node'), 'foo1')
        self.assertEqual(self._fs.get('ost')[1].get('index'), 0)

    def testSameIndexedDefined(self):
        """filesystem with same index used twice"""
        self.assertRaises(ConfigInvalidFileSystem, self.makeConfFileSystem, """
fs_name: example
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp0
mgt: node=foo1
mdt: node=foo2
ost: node=foo2 index=0
ost: node=foo1 index=0
""")

    def make_fs_with_backend(self, backend, text):
        """
        Create a FileSystem instance from text with a specific backend
        instance.
        """
        self._testfile = makeTempFile(text)
        fs = FileSystem(self._testfile.name)
        fs.backend = backend
        fs.setup_target_devices()
        return fs

    def test_match_device_simple_ha_node(self):
        """test target.match_device() with a simple ha_node"""

        # Dummy backend
        class DummyBackend(Backend):
            def start(self):
                pass
            def get_target_devices(self, target, fs_name=None, update_mode=None):
                return [TargetDevice('mgt', {'node': 'foo1', 'ha_node': ['foo2']}),
                        TargetDevice('mgt', {'node': 'foo1', 'ha_node': ['foo3']})]

        # Test with 1 matching ha_node
        fs = self.make_fs_with_backend(DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp0
mgt: node=foo1 ha_node=foo2
""")
        self.assertEqual(len(fs.get('mgt')), 1)

        # Test with 1 matching ha_node (bis)
        fs = self.make_fs_with_backend(DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp0
mgt: node=foo1 ha_node=foo3
""")
        self.assertEqual(len(fs.get('mgt')), 1)

        # Test without ha_node
        fs = self.make_fs_with_backend(DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp0
mgt: node=foo1
""")
        fs.setup_target_devices()

        # Test with no matching ha_node
        self.assertRaises(ConfigDeviceNotFoundError, self.make_fs_with_backend,
                          DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-4] nids=foo[1-4]@tcp0
mgt: node=foo1 ha_node=foo4
""")

    def test_match_device_multiple_ha_node(self):
        """test target.match_device() with a several ha_node"""

        # Dummy backend
        class DummyBackend(Backend):
            def start(self):
                pass
            def get_target_devices(self, target, fs_name=None, update_mode=None):
                return [TargetDevice('mgt', {'node': 'foo1', 'ha_node': ['foo2', 'foo3']}),
                        TargetDevice('mgt', {'node': 'foo1', 'ha_node': ['foo2', 'foo4']})]

        # Test with 2 matching ha_nodes
        fs = self.make_fs_with_backend(DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-4] nids=foo[1-4]@tcp0
mgt: node=foo1 ha_node=foo2 ha_node=foo3
""")
        self.assertEqual(len(fs.get('mgt')), 1)

        # Test with 1 matching ha_node
        fs = self.make_fs_with_backend(DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp0
mgt: node=foo1 ha_node=foo2
""")
        self.assertEqual(len(fs.get('mgt')), 2)

        # Test without ha_node
        fs = self.make_fs_with_backend(DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp0
mgt: node=foo1
""")
        self.assertEqual(len(fs.get('mgt')), 2)

    def test_backend_same_indexed_defined(self):
        """filesystem with backend and same index used twice"""

        # Dummy backend
        class DummyBackend(Backend):
            def start(self):
                pass
            def get_target_devices(self, target, fs_name=None, update_mode=None):
                return [TargetDevice('mgt', {'node': 'foo1', 'ha_node': ['foo2', 'foo3']}),
                        TargetDevice('mdt', {'node': 'foo2', 'ha_node': ['foo1', 'foo3']}),
                        TargetDevice('ost', {'node': 'foo1', 'ha_node': ['foo2', 'foo3']}),
                        TargetDevice('ost', {'node': 'foo2', 'ha_node': ['foo3', 'foo1']})]

        self.assertRaises(ConfigInvalidFileSystem, self.make_fs_with_backend, DummyBackend(), """
fs_name: example
nid_map: nodes=foo[1-2] nids=foo[1-2]@tcp0
mgt: node=foo1
mdt: node=foo2
ost: node=foo2 index=0
ost: node=foo1 index=0
""")

class FileSystemCompareTest(unittest.TestCase):

    def setUp(self):
        setup_tempdirs()

    def tearDown(self):
        clean_tempdirs()

    def _compare(self, orig, new):
        tmpfile = makeTempFile(textwrap.dedent(orig))
        origconf = FileSystem(tmpfile.name)
        newfile = makeTempFile(textwrap.dedent(new))
        newconf = FileSystem(newfile.name)
        return origconf.compare(newconf)

    def test_forbidden(self):
        self.assertRaises(ConfigException, self._compare,
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
""",
"""fs_name: compar2
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
""")

    def test_forbidden_target(self):
        self.assertRaises(ConfigException, self._compare,
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
ost: node=foo2 dev=/dev/sda jdev=/dev/sdb
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
ost: node=foo2 dev=/dev/sda jdev=/dev/sdc
""")

    def test_only_description(self):
        actions = self._compare(
"""fs_name: compare
description: foo
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
""",
"""fs_name: compare
description: bar
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
""")
        self.assertEqual(len(actions), 1)
        self.assertTrue(actions.get('copyconf', False))

    def test_no_difference(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
""")
        self.assertEqual(len(actions), 0)

    def test_clients_path(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 mode=external
client: node=foo[2,3] mount_path=/mypath
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 mode=external
client: node=foo2 mount_path=/mypath
client: node=foo3 mount_path=/mypath2
""")
        self.assertEqual(len(actions), 3)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue('unmount' in actions)
        self.assertTrue('mount' in actions)

    def test_nid_change(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@o2ib
mgt: node=foo1 dev=/dev/sda
""")
        self.assertEqual(len(actions), 2)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('writeconf', False))

    def test_add_ost(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda
ost: node=foo3 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda
ost: node=foo3 dev=/dev/sda
ost: node=foo4 dev=/dev/sda
""")
        self.assertEqual(len(actions), 3)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('format', False))
        self.assertTrue(actions.get('start', False))

    def test_remove_target(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda
ost: node=foo3 dev=/dev/sda
ost: node=foo4 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda
ost: node=foo3 dev=/dev/sda
""")
        self.assertEqual(len(actions), 4)
        self.assertEqual(actions.get('copyconf'), True)
        self.assertEqual(actions.get('writeconf'), True)
        self.assertEqual(len(actions.get('stop', [])), 1)
        self.assertEqual(len(actions.get('remove', [])), 1)

    def test_remove_router(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
router: node=foo1
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
router: node=foo2
""")
        self.assertEqual(len(actions), 3)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('stop', False))
        self.assertTrue(actions.get('start', False))

    def test_mkfs_options(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt_mkfs_options: -m0
mgt: node=foo1 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
""")
        self.assertEqual(len(actions), 2)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('reformat', False))

    def test_quota_options(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
quota: no
mgt: node=foo1 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
quota: yes
mgt: node=foo1 dev=/dev/sda
""")
        self.assertEqual(len(actions), 2)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('tunefs', False))

    def test_stripping_options(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
stripe_count: 1
mgt: node=foo1 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
stripe_count: 2
mgt: node=foo1 dev=/dev/sda
""")
        self.assertEqual(len(actions), 2)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('tunefs', False))

    def test_target_mount_options(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt_mount_options: ro
mgt: node=foo1 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
""")
        self.assertEqual(len(actions), 2)
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('restart', False))

    def test_client_mount_options_no_clients(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /foo
mgt: node=foo1 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /bar
mgt: node=foo1 dev=/dev/sda
""")
        self.assertEqual(list(actions.keys()), ['copyconf'])
        self.assertTrue(actions.get('copyconf', False))

    def test_client_mount_options(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /foo
mgt: node=foo1 dev=/dev/sda
client: node=foo2
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /bar
mgt: node=foo1 dev=/dev/sda
client: node=foo2
""")
        self.assertEqual(len(actions), 3)
        self.assertTrue(actions.get('copyconf', False))
        self.assertEqual(len(actions.get('mount', [])), 1)
        self.assertEqual(len(actions.get('unmount', [])), 1)

    def test_client_mount_path_and_remove(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /foo
mgt: node=foo1 dev=/dev/sda
client: node=foo[2-3]
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /bar
mgt: node=foo1 dev=/dev/sda
client: node=foo2
""")
        self.assertEqual(sorted(actions.keys()),
                         ['copyconf', 'mount', 'unmount'])
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('unmount', False))
        self.assertTrue(actions.get('mount', False))

    def test_per_client_mount_options_update(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /foo
mgt: node=foo1 dev=/dev/sda
client: node=foo2
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mount_path: /foo
mgt: node=foo1 dev=/dev/sda
client: node=foo2 mount_options=ro
""")
        self.assertEqual(sorted(actions.keys()),
                         ['copyconf', 'mount', 'unmount'])
        self.assertTrue(actions.get('copyconf', False))
        self.assertTrue(actions.get('unmount', False))
        self.assertTrue(actions.get('mount', False))

    def test_update_target_ha_node(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda
ost: node=foo3 dev=/dev/sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda ha_node=foo1
ost: node=foo3 dev=/dev/sda
""")
        self.assertEqual(len(actions), 4)
        self.assertEqual(actions.get('copyconf'), True)
        self.assertEqual(actions.get('writeconf'), True)
        self.assertEqual(len(actions.get('stop', [])), 1)
        self.assertEqual(actions.get('stop')[0].dic,
                          {'node':'foo2', 'dev':'/dev/sda'})
        self.assertEqual(len(actions.get('start', [])), 1)
        self.assertEqual(actions.get('start')[0].dic,
                          {'node':'foo2', 'dev':'/dev/sda', 'ha_node':['foo1']})

    def test_update_target_tag(self):
        actions = self._compare(
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda
ost: node=foo3 dev=/dev/sda tag=ost_foo3_dev_sda
""",
"""fs_name: compare
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
mgt: node=foo1 dev=/dev/sda
mdt: node=foo2 dev=/dev/sda
ost: node=foo3 dev=/dev/sda tag=ost_fooE_dev_sda
""")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions.get('copyconf'), True)

    def test_update_nid_map_targets(self):
        actions = self._compare(
            """fs_name: compare
            nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp
            mgt: node=foo1 dev=/dev/sda
            mdt: node=foo2 dev=/dev/sda
            ost: node=foo3 dev=/dev/sda
            """,
            """fs_name: compare
            nid_map: nodes=foo[1-3] nids=foo[1-3]@o2ib
            mgt: node=foo1 dev=/dev/sda
            mdt: node=foo2 dev=/dev/sda
            ost: node=foo3 dev=/dev/sda
            """)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions.get('copyconf'), True)
        self.assertEqual(actions.get('writeconf'), True)

    def test_update_nid_map_clients(self):
        actions = self._compare(
            """fs_name: compare
            nid_map: nodes=foo[1-3] nids=foo[1-3]@tcp
            mgt: node=foo1 dev=/dev/sda
            mdt: node=foo2 dev=/dev/sda
            ost: node=foo3 dev=/dev/sda
            mount_path: /foo
            """,
            """fs_name: compare
            nid_map: nodes=foo[1-4] nids=foo[1-4]@tcp
            mgt: node=foo1 dev=/dev/sda
            mdt: node=foo2 dev=/dev/sda
            ost: node=foo3 dev=/dev/sda
            client: node=foo4
            """)
        self.assertEqual(len(actions), 2)
        self.assertTrue(actions.get('mount', False))
        self.assertEqual(actions.get('copyconf'), True)
