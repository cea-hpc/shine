#!/usr/bin/env python
# Shine.FSUtils test suite
# Written by A. Degremont 2010-11-20
# $Id$


"""Unit test for FSUtils"""

import unittest

from Utils import setup_tempdirs, clean_tempdirs
from Shine.FSUtils import create_lustrefs, open_lustrefs


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
