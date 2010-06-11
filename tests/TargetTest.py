#!/usr/bin/env python
# Shine.Lustre.Target test suite
# Written by A. Degremont 2010-06-11
# $Id$


"""Unit test for Target"""

import sys
import unittest

sys.path.insert(0, '../lib')

from ClusterShell.NodeSet import NodeSet

from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Server import Server
from Shine.Lustre.Target import Target, TargetError

class TargetTest(unittest.TestCase):

    def testHaNode(self):
        """test failover servers"""
        fs = FileSystem('nonreg')
        srv = Server('foo1', 'foo1@tcp')
        tgt = Target(fs, srv, 0, '/dev/null')
        self.assertEqual(tgt.server, srv)
        self.assertEqual(tgt.failservers, [])

        # Could not switch to an undefined failnode
        self.assertFalse(tgt.failover(NodeSet("foo1")))
        self.assertEqual(tgt.server, srv)

        # Add a failserver and switch to it
        foo2 = Server('foo2', 'foo2@tcp')
        tgt.add_server(foo2)
        self.assertEqual(tgt.failservers, [ foo2 ])
        self.assertTrue(tgt.failover(NodeSet("foo2")))
        self.assertEqual(tgt.server, foo2)

        # Add a 2nd failserver and switch to it
        foo3 = Server('foo3', 'foo3@tcp')
        tgt.add_server(foo3)
        self.assertEqual(tgt.failservers, [ foo2, foo3 ])
        self.assertTrue(tgt.failover(NodeSet("foo3")))
        self.assertEqual(tgt.server, foo3)

        # Switch with more than 1 candidate but only one exist
        self.assertTrue(tgt.failover(NodeSet("bar,foo2")))
        self.assertEqual(tgt.server, foo2)

        # Could not switch if more than one node matches
        self.assertRaises(TargetError, Target.failover, tgt, 
                          NodeSet("foo[2,3]"))


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TargetTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
