#!/usr/bin/env python
# Shine.Configuration.Configuration test suite
# Written by A. Degremont 2010-11-21
# $Id$


"""Unit test for Configuration"""

import unittest

from Utils import setup_tempdirs, clean_tempdirs
from Shine.Configuration.Configuration import Configuration


class ConfigurationTest(unittest.TestCase):

    def setUp(self):
        self._conf = None
        setup_tempdirs()

    def tearDown(self):
        if self._conf:
            self._conf.unregister_fs()
        clean_tempdirs()

    def test_accessors(self):
        """Configuration get_* accessors."""
        self._conf = Configuration.create_from_model("../conf/models/example.lmf")
        self.assertEqual(self._conf.get_stripecount(), 2)
        self.assertEqual(self._conf.get_stripesize(), 1048576)
        self.assertTrue(self._conf.get_cfg_filename())
