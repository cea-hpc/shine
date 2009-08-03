#!/usr/bin/env python
# Shine.Lustre.Server test suite
# Written by A. Degremont 2009-08-03
# $Id$


"""Unit test for Server"""

import sys
import unittest
import socket

sys.path.insert(0, '../lib')

from Shine.Lustre.Server import Server

class ServerTest(unittest.TestCase):

    def testStringRepr(self):
        """test string representation"""
        srv = Server('localhost', 'localhost@tcp')
        self.assertEqual(str(srv), 'localhost (localhost@tcp)')

    def testIsLocal(self):
        """test is_local()"""
        fqdn = socket.getfqdn()
        shortname = socket.gethostname().split('.', 1)[0]

        # Test shortname is local()
        srv = Server(shortname, '%s@tcp' % shortname)
        self.assertTrue(srv.is_local())

        # Test fqdn is local()
        srv = Server(fqdn, '%s@tcp' % fqdn)
        self.assertTrue(srv.is_local())

        # Test a dummy shortname should not be local
        shortname = shortname + "-shine-false-suffix"
        srv = Server(shortname, '%s@tcp' % shortname)
        self.assertFalse(srv.is_local())

        # Test a false domain name with a good hostname
        othername = shortname + ".shine-false-tld"
        srv = Server(othername, '%s@tcp' % othername)
        self.assertFalse(srv.is_local())

        # Test something else should not be local
        othername = fqdn + ".shine-false-tld"
        srv = Server(othername, '%s@tcp' % othername)
        self.assertFalse(srv.is_local())


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ServerTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
