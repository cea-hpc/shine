#!/usr/bin/env python
# Shine.FSUtils test suite
# Written by A. Degremont 2010-11-20
# $Id$


"""Unit test for FSUtils"""

import unittest

from Utils import setup_tempdirs, clean_tempdirs, makeTempFile

from Shine.FSUtils import create_lustrefs, open_lustrefs, RangeSet, NodeSet
from Shine.Lustre.FileSystem import MGT, MDT, OST, Router, Client

from Shine.Configuration.Globals import Globals


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
nid_map: nodes=foo[1-13] nids=foo[1-13]@tcp
client: node=foo[8-11]
mgt: node=foo1 dev=/dev/sda
mdt: node=foo1 dev=/dev/sdb
ost: node=foo2 dev=/dev/sdc ha_node=foo3 ha_node=foo4 #index 0
ost: node=foo2 dev=/dev/sdd ha_node=foo4 ha_node=foo3 #index 1
ost: node=foo3 dev=/dev/sdc ha_node=foo2 ha_node=foo4 #index 2
ost: node=foo3 dev=/dev/sdd ha_node=foo4 ha_node=foo2 #index 3
ost: node=foo5 dev=/dev/sde ha_node=foo6 ha_node=foo7 #index 4
ost: node=foo5 dev=/dev/sdf ha_node=foo7 ha_node=foo6 #index 5
ost: node=foo6 dev=/dev/sde ha_node=foo5 ha_node=foo7 #index 6
ost: node=foo6 dev=/dev/sdf ha_node=foo7 ha_node=foo5 #index 7
router: node=foo[12-13]
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
        self.assertEqual(len(comps), 8)
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
        self.assertEqual(len(comps), 9)
        self.assertEqual(comps[0].TYPE, Client.TYPE)
        self.assertEqual(comps[1].TYPE, MDT.TYPE)
        self.assertEqual(comps[2].TYPE, MGT.TYPE)
        self.assert_comp(comps[3], OST.TYPE, None, "/dev/sdc")
        self.assert_comp(comps[4], OST.TYPE, None, "/dev/sdd")
        self.assert_comp(comps[5], OST.TYPE, None, "/dev/sde")
        self.assert_comp(comps[6], OST.TYPE, None, "/dev/sdf")
        self.assertEqual(comps[7].TYPE, Router.TYPE)
        self.assertEqual(comps[8].TYPE, Router.TYPE)

    def test_action_enabled_nodes(self):
        # shine failover extended selection with nodes
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   nodes=NodeSet("foo[1,3]"),
                                   extended=True)
        comps = self.complist(fs)
        self.assertEqual(len(comps), 6)
        self.assertEqual(comps[0].TYPE, MDT.TYPE)
        self.assertEqual(comps[1].TYPE, MGT.TYPE)
        self.assert_comp(comps[2], OST.TYPE, None, "/dev/sdc")
        self.assert_comp(comps[3], OST.TYPE, None, "/dev/sdd")
        self.assert_comp(comps[4], OST.TYPE, None, "/dev/sdc")
        self.assert_comp(comps[5], OST.TYPE, None, "/dev/sdd")

        self.assertTrue(comps[0].server.action_enabled)
        self.assertTrue(comps[1].server.action_enabled)
        self.assertFalse(comps[2].server.action_enabled)
        self.assertFalse(comps[3].server.action_enabled)
        self.assertTrue(comps[4].server.action_enabled)
        self.assertTrue(comps[5].server.action_enabled)

    def test_action_enabled_exclude(self):
        # shine failover extended selection with exclude
        fsconf, fs = open_lustrefs(self.fsconf.get_fs_name(),
                                   excluded=NodeSet("foo[1,2-5,9-11]"),
                                   extended=True)
        comps = self.complist(fs)
        self.assertEqual(len(comps), 7)
        self.assertEqual(comps[0].TYPE, Client.TYPE)
        self.assert_comp(comps[1], OST.TYPE, None, "/dev/sde")
        self.assert_comp(comps[2], OST.TYPE, None, "/dev/sdf")
        self.assert_comp(comps[3], OST.TYPE, None, "/dev/sde")
        self.assert_comp(comps[4], OST.TYPE, None, "/dev/sdf")
        self.assertEqual(comps[5].TYPE, Router.TYPE)
        self.assertEqual(comps[6].TYPE, Router.TYPE)

        self.assertTrue(comps[0].server.action_enabled)
        self.assertFalse(comps[1].server.action_enabled)
        self.assertFalse(comps[2].server.action_enabled)
        self.assertTrue(comps[3].server.action_enabled)
        self.assertTrue(comps[4].server.action_enabled)
        self.assertTrue(comps[5].server.action_enabled)
