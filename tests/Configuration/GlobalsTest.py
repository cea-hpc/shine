#!/usr/bin/env python
# Shine.Configuration.Globals test suite
# Written by A. Degremont 2010-11-07
# $Id$


"""Unit test for Globals"""

import unittest

from Shine.Configuration.Globals import Globals


class GlobalsTest(unittest.TestCase):

    def testNoFileIsOk(self):
        """test that Globals load if not file is found"""
        self.assertEqual(Globals().get('backend'), 'None')

    def testLoadExample(self):
        backup = Globals.DEFAULT_CONF_FILE
        Globals.DEFAULT_CONF_FILE = "../conf/shine.conf"
        self.assertEqual(Globals().get('backend'), 'None')
        self.assertEqual(Globals().get('storage_file'),
                '/etc/shine/storage.conf')
        Globals.DEFAULT_CONF_FILE = backup

    def test_lustre_version(self):
        conf = Globals()
        self.assertFalse(conf.lustre_version_is_smaller('1.6.5'))

        conf.add('lustre_version', '1.8.5')
        self.assertFalse(conf.lustre_version_is_smaller('1.6.7'))
        self.assertTrue(conf.lustre_version_is_smaller('2.0.0.1'))
