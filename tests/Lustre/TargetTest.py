#!/usr/bin/env python
#
# Copyright (C) 2007-2013 CEA
#
# Shine.Lustre.Target test suite
#

"""Unit test for Target"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.NodeSet import NodeSet

from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Server import Server
from Shine.Lustre.Target import Target, ComponentError

class TargetTest(unittest.TestCase):

    def test_unique_id(self):
        """test target.uniqueid()"""
        fs1 = FileSystem('uniqueid')
        srv1 = Server('foo1', ['foo1@tcp'])
        tgt1 = fs1.new_target(srv1, 'ost', 0, '/dev/null')

        fs2 = FileSystem('uniqueid')
        srv2 = Server('foo1', ['foo1@tcp'])
        tgt2 = fs2.new_target(srv2, 'ost', 0, '/dev/null')

        self.assertEqual(tgt2.uniqueid(), tgt1.uniqueid())

    def test_unique_id_failover(self):
        """test target.uniqueid()"""
        fs1 = FileSystem('uniqueid')
        srv1a = Server('foo1', ['foo1@tcp'])
        srv1b = Server('foo2', ['foo2@tcp'])
        tgt1 = fs1.new_target(srv1a, 'ost', 0, '/dev/null')
        tgt1.add_server(srv1b)

        fs2 = FileSystem('uniqueid')
        srv2a = Server('foo1', ['foo1@tcp'])
        srv2b = Server('foo2', ['foo2@tcp'])
        tgt2 = fs2.new_target(srv2a, 'ost', 0, '/dev/null')
        tgt2.add_server(srv2b)
        tgt2.failover(NodeSet('foo2'))

        print tgt2.uniqueid()
        self.assertEqual(tgt2.uniqueid(), tgt1.uniqueid())

    def testAllServers(self):
        """test Target.allservers()"""
        fs1 = FileSystem('allsrvr')
        srv1 = Server('foo1', ['foo1@tcp'])
        srv2 = Server('foo2', ['foo2@tcp'])
        tgt = fs1.new_target(srv1, 'ost', 0, '/dev/null')
        tgt.add_server(srv2)
        self.assertEqual(list(iter(tgt.allservers())), [srv1, srv2])

    def testHaNode(self):
        """test failover servers"""
        fs = FileSystem('nonreg')
        srv = Server('foo1', ['foo1@tcp'])
        tgt = Target(fs, srv, 0, '/dev/null')
        self.assertEqual(tgt.server, srv)
        self.assertEqual(len(tgt.failservers), 0)

        # Could not switch to an undefined failnode
        self.assertFalse(tgt.failover(NodeSet("foo1")))
        self.assertEqual(tgt.server, srv)

        # Add a failserver and switch to it
        foo2 = Server('foo2', ['foo2@tcp'])
        tgt.add_server(foo2)
        self.assertEqual(list(tgt.failservers), [ foo2 ])
        self.assertTrue(tgt.failover(NodeSet("foo2")))
        self.assertEqual(tgt.server, foo2)

        # Add a 2nd failserver and switch to it
        foo3 = Server('foo3', ['foo3@tcp'])
        tgt.add_server(foo3)
        self.assertEqual(list(tgt.failservers), [ foo2, foo3 ])
        self.assertTrue(tgt.failover(NodeSet("foo3")))
        self.assertEqual(tgt.server, foo3)

        # Switch with more than 1 candidate but only one exist
        self.assertTrue(tgt.failover(NodeSet("bar,foo2")))
        self.assertEqual(tgt.server, foo2)

        # Could not switch if more than one node matches
        self.assertRaises(ComponentError, Target.failover, tgt,
                          NodeSet("foo[2,3]"))


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TargetTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
