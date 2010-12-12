#!/usr/bin/env python
# Shine.Configuration.FileSystem class
# Written by A. Degremont 2009-07-17
# $Id$


"""Unit test for Shine.Configuration.FileSystem"""

import unittest

from Utils import makeTempFile, setup_tempdirs, clean_tempdirs
from Shine.Configuration.FileSystem import FileSystem
from Shine.Configuration.Exceptions import ConfigException, ConfigInvalidFileSystem

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
        self.assertEqual(len(fs.model), 20)

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


class FileSystemCompareTest(unittest.TestCase):

    def setUp(self):
        setup_tempdirs()

    def tearDown(self):
        clean_tempdirs()

    def _compare(self, orig, new):
        tmpfile = makeTempFile(orig)
        origconf = FileSystem(tmpfile.name)
        newfile = makeTempFile(new)
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
