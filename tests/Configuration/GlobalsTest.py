#!/usr/bin/env python
# Shine.Configuration.Globals test suite
# Written by A. Degremont 2010-11-07
# $Id$


"""Unit test for Globals"""

import unittest

from Shine.Configuration.Globals import Globals


class GlobalsTest(unittest.TestCase):

    def testLoadExample(self):
        Globals.DEFAULT_CONF_FILE = "../conf/shine.conf"
        self.assertEqual(Globals().get('backend'), 'None')
        self.assertEqual(Globals().get('storage_file'),
                '/etc/shine/storage.conf')
