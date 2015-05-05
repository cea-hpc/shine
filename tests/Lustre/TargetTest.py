#!/usr/bin/env python
#
# Copyright (C) 2007-2013 CEA
#
# Shine.Lustre.Target test suite
#

"""Unit test for Target"""

import unittest

from ClusterShell.NodeSet import NodeSet

from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Server import Server
from Shine.Lustre.Target import Target, ComponentError
from Shine.Lustre.Component import MOUNTED, RECOVERING, OFFLINE, MIGRATED, \
                                   TARGET_ERROR, RUNTIME_ERROR

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


class GetStateTest(unittest.TestCase):

    def setUp(self):
        fs1 = FileSystem('allsrvr')
        self.srv1 = Server('foo1', ['foo1@tcp'])
        self.srv2 = Server('foo2', ['foo2@tcp'])
        self.srv3 = Server('foo3', ['foo3@tcp'])

        self.srv1name = str(self.srv1.hostname)
        self.srv2name = str(self.srv2.hostname)
        self.srv3name = str(self.srv3.hostname)

        self.tgt = fs1.new_target(self.srv1, 'ost', 0, '/dev/null')
        self.tgt.add_server(self.srv2)
        self.tgt.add_server(self.srv3)

    def test_master_and_none(self):
        """test master node has a state and all others have none"""
        # Master has a state, all others have none
        self.tgt._states = {self.srv1name: MOUNTED,
                            self.srv2name: None,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, MOUNTED)

        self.tgt._states = {self.srv1name: RECOVERING,
                            self.srv2name: None,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, RECOVERING)

        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: None,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, OFFLINE)

        self.tgt._states = {self.srv1name: TARGET_ERROR,
                            self.srv2name: None,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, TARGET_ERROR)

        self.tgt._states = {self.srv1name: RUNTIME_ERROR,
                            self.srv2name: None,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)

    def test_failover_and_none(self):
        """test failover node has a state and all others have none"""
        # One failover has a state, all others have none
        self.tgt._states = {self.srv1name: None,
                            self.srv2name: MOUNTED,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, MIGRATED)

        self.tgt._states = {self.srv1name: None,
                            self.srv2name: RECOVERING,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, RECOVERING)

        self.tgt._states = {self.srv1name: None,
                            self.srv2name: OFFLINE,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, OFFLINE)

        self.tgt._states = {self.srv1name: None,
                            self.srv2name: TARGET_ERROR,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, TARGET_ERROR)

        self.tgt._states = {self.srv1name: None,
                            self.srv2name: RUNTIME_ERROR,
                            self.srv3name: None}
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)

    def test_two_nodes_started(self):
        """test component started on two different nodes"""
        # Two nodes have state MOUNTED or RECOVERING
        self.tgt._states = {self.srv1name: None,
                            self.srv2name: MOUNTED,
                            self.srv3name: MOUNTED}
        self.assertEqual(self.tgt.state, TARGET_ERROR)

        self.tgt._states = {self.srv1name: None,
                            self.srv2name: MOUNTED,
                            self.srv3name: RECOVERING}
        self.assertEqual(self.tgt.state, TARGET_ERROR)

    def test_recovering_stays_recovering(self):
        """test recovering is displayed whatever the node"""
        # Recovering is always Recovering
        self.tgt._states = {self.srv1name: RECOVERING,
                            self.srv2name: OFFLINE,
                            self.srv3name: OFFLINE}
        self.assertEqual(self.tgt.state, RECOVERING)

        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: OFFLINE,
                            self.srv3name: RECOVERING}
        self.assertEqual(self.tgt.state, RECOVERING)

    def test_various_states(self):
        """test various states"""
        # Various states
        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: OFFLINE,
                            self.srv3name: OFFLINE}
        self.assertEqual(self.tgt.state, OFFLINE)

        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: OFFLINE,
                            self.srv3name: TARGET_ERROR}
        self.assertEqual(self.tgt.state, OFFLINE)

        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: OFFLINE,
                            self.srv3name: RUNTIME_ERROR}
        self.assertEqual(self.tgt.state, OFFLINE)

        self.tgt._states = {self.srv1name: MOUNTED,
                            self.srv2name: OFFLINE,
                            self.srv3name: OFFLINE}
        self.assertEqual(self.tgt.state, MOUNTED)

        self.tgt._states = {self.srv1name: MOUNTED,
                            self.srv2name: OFFLINE,
                            self.srv3name: TARGET_ERROR}
        self.assertEqual(self.tgt.state, MOUNTED)

        self.tgt._states = {self.srv1name: MOUNTED,
                            self.srv2name: OFFLINE,
                            self.srv3name: RUNTIME_ERROR}
        self.assertEqual(self.tgt.state, MOUNTED)

        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: OFFLINE,
                            self.srv3name: MOUNTED}
        self.assertEqual(self.tgt.state, MIGRATED)

        self.tgt._states = {self.srv1name: TARGET_ERROR,
                            self.srv2name: OFFLINE,
                            self.srv3name: MOUNTED}
        self.assertEqual(self.tgt.state, MIGRATED)

        self.tgt._states = {self.srv1name: RUNTIME_ERROR,
                            self.srv2name: OFFLINE,
                            self.srv3name: MOUNTED}
        self.assertEqual(self.tgt.state, MIGRATED)

    def test_update_server(self):
        """test Target.update_server()"""
        self.tgt._states = {self.srv1name: None,
                            self.srv2name: None,
                            self.srv3name: None}
        self.assertTrue(self.tgt.update_server())
        self.assertEqual(self.tgt.server, self.srv1)

        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: OFFLINE,
                            self.srv3name: OFFLINE}
        self.assertTrue(self.tgt.update_server())
        self.assertEqual(self.tgt.server, self.srv1)

        self.tgt._states = {self.srv1name: MOUNTED,
                            self.srv2name: OFFLINE,
                            self.srv3name: OFFLINE}
        self.assertTrue(self.tgt.update_server())
        self.assertEqual(self.tgt.server, self.srv1)

        self.tgt._states = {self.srv1name: OFFLINE,
                            self.srv2name: MOUNTED,
                            self.srv3name: OFFLINE}
        self.assertTrue(self.tgt.update_server())
        self.assertEqual(self.tgt.server, self.srv2)

        self.tgt._states = {self.srv1name: MOUNTED,
                            self.srv2name: OFFLINE,
                            self.srv3name: TARGET_ERROR}
        self.assertTrue(self.tgt.update_server())
        self.assertEqual(self.tgt.server, self.srv1)

        self.tgt._states = {self.srv1name: RUNTIME_ERROR,
                            self.srv2name: TARGET_ERROR,
                            self.srv3name: RECOVERING}
        self.assertTrue(self.tgt.update_server())
        self.assertEqual(self.tgt.server, self.srv3)

        self.tgt._states = {self.srv1name: MOUNTED,
                            self.srv2name: OFFLINE,
                            self.srv3name: RECOVERING}
        self.assertFalse(self.tgt.update_server())
        self.assertEqual(self.tgt.server, self.srv1)
