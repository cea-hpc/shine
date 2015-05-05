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

class StateTest(unittest.TestCase):
    def test_get_state(self):
        """test get_state function"""
        fs1 = FileSystem('allsrvr')
        srv1 = Server('foo1', ['foo1@tcp'])
        srv2 = Server('foo2', ['foo2@tcp'])
        srv3 = Server('foo3', ['foo3@tcp'])
        srv4 = Server('foo4', ['foo4@tcp'])
        tgt = fs1.new_target(srv1, 'ost', 0, '/dev/null')
        tgt.add_server(srv2)
        tgt.add_server(srv3)
        tgt.add_server(srv4)

        # Master has a state, all others have none
        tgt._states = {srv1: MOUNTED, srv2: None, srv3: None, srv4: None}
        self.assertEqual(tgt.state, MOUNTED)
        tgt._states = {srv1: RECOVERING, srv2: None, srv3: None, srv4: None}
        self.assertEqual(tgt.state, RECOVERING)
        tgt._states = {srv1: OFFLINE, srv2: None, srv3: None, srv4: None}
        self.assertEqual(tgt.state, OFFLINE)
        tgt._states = {srv1: TARGET_ERROR, srv2: None, srv3: None, srv4: None}
        self.assertEqual(tgt.state, TARGET_ERROR)
        tgt._states = {srv1: RUNTIME_ERROR, srv2: None, srv3: None, srv4: None}
        self.assertEqual(tgt.state, RUNTIME_ERROR)

        # One failover has a state, all others have none
        tgt._states = {srv1: None, srv2: MOUNTED, srv3: None, srv4: None}
        self.assertEqual(tgt.state, MIGRATED)
        tgt._states = {srv1: None, srv2: RECOVERING, srv3: None, srv4: None}
        self.assertEqual(tgt.state, RECOVERING)
        tgt._states = {srv1: None, srv2: OFFLINE, srv3: None, srv4: None}
        self.assertEqual(tgt.state, OFFLINE)
        tgt._states = {srv1: None, srv2: TARGET_ERROR, srv3: None, srv4: None}
        self.assertEqual(tgt.state, TARGET_ERROR)
        tgt._states = {srv1: None, srv2: RUNTIME_ERROR, srv3: None, srv4: None}
        self.assertEqual(tgt.state, RUNTIME_ERROR)

        # Two nodes have state MOUNTED or RECOVERING
        tgt._states = {srv1: None, srv2: MOUNTED, srv3: MOUNTED, srv4: None}
        self.assertEqual(tgt.state, TARGET_ERROR)
        tgt._states = {srv1: None, srv2: MOUNTED, srv3: RECOVERING, srv4: None}
        self.assertEqual(tgt.state, TARGET_ERROR)

        # Various states
        tgt._states = {srv1: OFFLINE, srv2: OFFLINE, srv3: OFFLINE, srv4: OFFLINE}
        self.assertEqual(tgt.state, OFFLINE)
        tgt._states = {srv1: OFFLINE, srv2: OFFLINE, srv3: OFFLINE, srv4: TARGET_ERROR}
        self.assertEqual(tgt.state, OFFLINE)
        tgt._states = {srv1: OFFLINE, srv2: OFFLINE, srv3: OFFLINE, srv4: RUNTIME_ERROR}
        self.assertEqual(tgt.state, OFFLINE)
        tgt._states = {srv1: MOUNTED, srv2: OFFLINE, srv3: OFFLINE, srv4: OFFLINE}
        self.assertEqual(tgt.state, MOUNTED)
        tgt._states = {srv1: MOUNTED, srv2: OFFLINE, srv3: TARGET_ERROR, srv4: OFFLINE}
        self.assertEqual(tgt.state, MOUNTED)
        tgt._states = {srv1: MOUNTED, srv2: OFFLINE, srv3: RUNTIME_ERROR, srv4: OFFLINE}
        self.assertEqual(tgt.state, MOUNTED)
        tgt._states = {srv1: OFFLINE, srv2: OFFLINE, srv3: OFFLINE, srv4: MOUNTED}
        self.assertEqual(tgt.state, MIGRATED)
        tgt._states = {srv1: TARGET_ERROR, srv2: OFFLINE, srv3: OFFLINE, srv4: MOUNTED}
        self.assertEqual(tgt.state, MIGRATED)
        tgt._states = {srv1: RUNTIME_ERROR, srv2: OFFLINE, srv3: OFFLINE, srv4: MOUNTED}
        self.assertEqual(tgt.state, MIGRATED)

        # Recovering is always Recovering
        tgt._states = {srv1: RECOVERING, srv2: OFFLINE, srv3: OFFLINE, srv4: OFFLINE}
        self.assertEqual(tgt.state, RECOVERING)
        tgt._states = {srv1: OFFLINE, srv2: OFFLINE, srv3: RECOVERING, srv4: OFFLINE}
        self.assertEqual(tgt.state, RECOVERING)
