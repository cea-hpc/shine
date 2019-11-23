#!/usr/bin/env python
# Shine.Lustre.Client test suite
# Written by A. Degremont 2010-12-20

"""Unit test for Client"""

import unittest

from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Server import Server
from Shine.Lustre.Client import Client

class ClientTest(unittest.TestCase):

    def test_allservers(self):
        """test client.allservers()"""
        fs = FileSystem('foo')
        srv = Server('foo1', ['foo1@tcp'])
        client = fs.new_client(srv, '/foo')
        self.assertEqual(str(client.allservers().nodeset()), 'foo1')

    def test_unique_id(self):
        """test client.uniqueid()"""
        fs1 = FileSystem('uniqueid')
        srv1 = Server('foo1', ['foo1@tcp'])
        client1 = fs1.new_client(srv1, '/foo')

        fs2 = FileSystem('uniqueid')
        srv2 = Server('foo1', ['foo1@tcp'])
        client2 = fs2.new_client(srv2, '/foo')

        self.assertEqual(client1.uniqueid(), client2.uniqueid())

    def test_uniqueid_diff_mountpath(self):
        """test client.uniqueid() (diff mount_path)"""
        fs1 = FileSystem('uniqueid')
        srv1 = Server('foo1', ['foo1@tcp'])
        client1 = fs1.new_client(srv1, '/foo1')

        fs2 = FileSystem('uniqueid')
        srv2 = Server('foo1', ['foo1@tcp'])
        client2 = fs2.new_client(srv2, '/foo2')

        self.assertNotEqual(client1.uniqueid(), client2.uniqueid())
