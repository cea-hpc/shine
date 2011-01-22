#!/usr/bin/env python
# Shine.FSUtils test suite
# Written by A. Degremont 2010-11-20
# $Id$


"""Unit test for FSUtils"""

import unittest

from Utils import setup_tempdirs, clean_tempdirs, makeTempFile

from Shine.FSUtils import create_lustrefs, open_lustrefs, RangeSet, NodeSet
from Shine.Lustre.FileSystem import MGT, MDT, OST, Router, Client


class FSUtilsTest(unittest.TestCase):

    def setUp(self):
        setup_tempdirs()

    def tearDown(self):
        clean_tempdirs()

    def test_create_example(self):
        fsconf, fs = create_lustrefs("../conf/models/example.lmf")
        self.assertTrue(fsconf)
        self.assertTrue(fs)
        fsconf.unregister_fs()

    def test_open_from_cache(self):
        # First, store example in cache
        fsconf, fs = create_lustrefs("../conf/models/example.lmf")
        self.assertTrue(fsconf)
        self.assertTrue(fs)

        # Try to re-read them
        fsconf, fs = open_lustrefs(fsconf.get_fs_name())
        self.assertTrue(fsconf)
        self.assertTrue(fs)

        fsconf.unregister_fs()

class FSUtilParamTest(FSUtilsTest):

    def setUp(self):
        FSUtilsTest.setUp(self)

        tmpfile = makeTempFile("""
fs_name: param
nid_map: nodes=foo[1-10] nids=foo[1-10]@tcp
client: node=foo[7-10]
mgt: node=foo1 dev=/dev/sda
mdt: node=foo1 dev=/dev/sdb
ost: node=foo2 dev=/dev/sdc ha_node=foo3 ha_node=foo4 #index 0
ost: node=foo2 dev=/dev/sdd ha_node=foo4 ha_node=foo3 #index 1
ost: node=foo3 dev=/dev/sdc ha_node=foo2 ha_node=foo4 #index 2
ost: node=foo3 dev=/dev/sdd ha_node=foo4 ha_node=foo2 #index 3
router: node=foo[5-6]
mount_path: /param
        """)
        self.fsconf, self.fs = create_lustrefs(tmpfile.name)

    def tearDown(self):
        self.fsconf.unregister_fs()
        FSUtilsTest.tearDown(self)

    @classmethod
    def complist(cfs, fs):
        key = lambda comp: (comp.TYPE, getattr(comp, 'index', 0))
        return list(sorted(fs.components.enabled(), key=key))

    def assert_comp(self, comp, tgt_type, index=None, dev=None):
        self.assertEqual(comp.TYPE, tgt_type)
        if index is not None:
            self.assertEqual(comp.index, index)
        if dev is not None:
            self.assertEqual(comp.dev, dev)

    def test_target_only(self):
        # shine -f param -t ost
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   target_types='ost')
        comps = self.complist(fs)
        self.assertEqual(len(comps), 4)
        for tgt in comps:
            self.assertEqual(tgt.TYPE, OST.TYPE)

    def test_target_index(self):
        # shine -f param -t ost -i 1
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   target_types='ost',
                                   indexes=RangeSet("1"))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 1)
        self.assert_comp(comps[0], OST.TYPE, 1)

    def test_target_index_failover(self):
        # shine -f param -t ost -i 1 -F foo2
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   target_types='ost',
                                   failover=NodeSet('foo2'))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 2)
        self.assert_comp(comps[0], OST.TYPE, 2, "/dev/sdc")
        self.assert_comp(comps[1], OST.TYPE, 3, "/dev/sdd")

    def test_target_index_unknown_failover(self):
        # shine -f param -t ost -i 1 -F foo5
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   target_types='ost',
                                   failover=NodeSet('foo5'),
                                   indexes=RangeSet("1"))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 0)

    def test_target_nodes_failover(self):
        # shine -f param -t ost -n foo2 -F foo3
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   target_types='ost',
                                   nodes=NodeSet('foo3'),
                                   failover=NodeSet('foo3'))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 2)
        self.assert_comp(comps[0], OST.TYPE, 0, "/dev/sdc")
        self.assert_comp(comps[1], OST.TYPE, 1, "/dev/sdd")

    def test_target_index_nodes_failover(self):
        # shine -f param -t ost -n foo2 -F foo3 -i 3
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   target_types='ost',
                                   nodes=NodeSet('foo3'),
                                   failover=NodeSet('foo3'),
                                   indexes=RangeSet('1'))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 1)
        self.assert_comp(comps[0], OST.TYPE, 1, "/dev/sdd")

    def test_label(self):
        # shine -f param -l param-MDT0000
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   labels=NodeSet("param-MDT0000"))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 1)
        self.assert_comp(comps[0], MDT.TYPE, 0)

    def test_nodes_target(self):
        # shine -f param -t ost -n foo2
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   target_types='ost',
                                   nodes=NodeSet('foo2'))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 2)
        self.assert_comp(comps[0], OST.TYPE, 0, "/dev/sdc")
        self.assert_comp(comps[1], OST.TYPE, 1, "/dev/sdd")

    def test_exclude(self):
        # shine -f param -x foo[3,5,8-10]
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   excluded=NodeSet("foo[3,5,8-10]"))
        comps = self.complist(fs)
        self.assertEqual(len(comps), 6)
        self.assertEqual(comps[0].TYPE, Client.TYPE)
        self.assertEqual(comps[1].TYPE, MDT.TYPE)
        self.assertEqual(comps[2].TYPE, MGT.TYPE)
        self.assert_comp(comps[3], OST.TYPE, None, "/dev/sdc")
        self.assert_comp(comps[4], OST.TYPE, None, "/dev/sdd")
        self.assertEqual(comps[5].TYPE, Router.TYPE)
