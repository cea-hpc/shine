#!/usr/bin/env python
# Shine.Lustre.Server test suite
# Written by A. Degremont 2009-08-03


"""Unit test for Server"""

import unittest
import socket

from Shine.Lustre.Server import Server, ServerGroup
# No direct dependancies to NodeSet. This should be fixed.
from ClusterShell.NodeSet import NodeSet

class ServerTest(unittest.TestCase):

    def testStringRepr(self):
        """test string representation"""
        srv = Server('localhost', ['localhost@tcp'])
        self.assertEqual(str(srv), 'localhost (localhost@tcp)')

    def testHostname(self):
        """test hostname resolution"""
        # Check hostname methods returns something
        self.assertTrue(Server.hostname_short())
        self.assertTrue(Server.hostname_long())

    def testIsLocal(self):
        """test is_local()"""
        fqdn = socket.getfqdn()
        shortname = socket.gethostname().split('.', 1)[0]

        # Test shortname is local()
        srv = Server(shortname, ['%s@tcp' % shortname])
        self.assertTrue(srv.is_local())

        # Test fqdn is local()
        srv = Server(fqdn, ['%s@tcp' % fqdn])
        self.assertTrue(srv.is_local())

        # Test a dummy shortname should not be local
        shortname = shortname + "-shine-false-suffix"
        srv = Server(shortname, ['%s@tcp' % shortname])
        self.assertFalse(srv.is_local())

        # Test a false domain name with a good hostname
        othername = shortname + ".shine-false-tld"
        srv = Server(othername, ['%s@tcp' % othername])
        self.assertFalse(srv.is_local())

        # Test something else should not be local
        othername = fqdn + ".shine-false-tld"
        srv = Server(othername, ['%s@tcp' % othername])
        self.assertFalse(srv.is_local())

        # Check hostname methods are rightly seen as local
        self.assertTrue(Server(Server.hostname_short(), ['foo']).is_local())
        self.assertTrue(Server(Server.hostname_long(), ['foo']).is_local())

    def testDistantServers(self):
        """test distant_servers()"""
        nodes = NodeSet("foo,bar")
        self.assertEqual(Server.distant_servers(nodes), nodes)

        nodes_short = nodes | NodeSet(Server.hostname_short())
        self.assertEqual(Server.distant_servers(nodes_short), nodes)

        nodes_long = nodes | NodeSet(Server.hostname_long())
        self.assertEqual(Server.distant_servers(nodes_long), nodes)


class ServerGroupTest(unittest.TestCase):

    def testSimple(self):
        """test ServerGroup simple tests"""
        grp = ServerGroup()
        self.assertEqual(len(grp), 0)

        srv = Server('foo', ['foo@tcp'])
        grp.append(srv)
        self.assertEqual(len(grp), 1)
        self.assertEqual(grp[0], srv)

    def testIter(self):
        """test ServerGroup.__iter__()"""
        srv1 = Server('foo1', ['foo1@tcp'])
        srv2 = Server('foo2', ['foo2@tcp'])
        grp = ServerGroup([srv1, srv2])
        self.assertEqual(list(iter(grp)), [srv1, srv2])

    def testSelect(self):
        """test ServerGroup.select()"""
        srv1 = Server('foo1', ['foo1@tcp'])
        srv2 = Server('foo2', ['foo2@tcp'])
        srv3 = Server('foo3', ['foo3@tcp'])
        grp = ServerGroup([srv1, srv2, srv3])
        subgrp = grp.select(NodeSet("foo[1,3]"))
        self.assertEqual(list(iter(subgrp)), [srv1, srv3])

    def testNodeSet(self):
        """test ServerGroup.nodeset()"""
        srv1 = Server('foo1', ['foo1@tcp'])
        srv2 = Server('foo2', ['foo2@tcp'])
        grp = ServerGroup([srv1, srv2])
        self.assertEqual(grp.nodeset(), NodeSet('foo[1-2]'))

    def testDistant(self):
        """test ServerGroup.nodeset()"""
        fqdn = socket.getfqdn()
        shortname = socket.gethostname().split('.', 1)[0]

        srv1 = Server(shortname, ['%s@tcp' % shortname])
        srv2 = Server('foo', ['foo@tcp'])
        grp = ServerGroup([srv1, srv2])
        subgrp = grp.distant()
        self.assertEqual(list(iter(subgrp)), [ srv2 ])
