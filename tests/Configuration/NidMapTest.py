#!/usr/bin/env python
# Shine.Configuration.NidMap test suite
# Written by A. Degremont 2010-09-25


"""Unit test for Nid Mapping management"""

import unittest

from Shine.Configuration.NidMap import NidMap, InvalidNidMapError
from Shine.Configuration.Model import Model
from Shine.Configuration.Model import NidMap as ModelNidMap

class NidMapTest(unittest.TestCase):

    def testEmpty(self):
        """empty nidmap"""
        nm = NidMap()

    def testSimple(self):
        """simple mapping"""
        nm = NidMap("foo[1-2]", "foo[1-2]@o2ib2")
        self.assertEqual(nm["foo1"], ["foo1@o2ib2"])
        self.assertEqual(nm["foo2"], ["foo2@o2ib2"])

    def testAddMapping(self):
        """add() method"""
        nm = NidMap()
        nm.add("bar[1-3]", "bar[1-3]-ib0@o2ib3")
        self.assertEqual(nm["bar1"], ["bar1-ib0@o2ib3"])
        self.assertEqual(nm["bar2"], ["bar2-ib0@o2ib3"])

    def testString(self):
        """cast to string is ok"""
        nm = NidMap("foo[1-2]", "foo[1-2]@o2ib2")
        str(nm)

    def testWrongRanges(self):
        """ranges do not match"""
        self.assertRaises(InvalidNidMapError, NidMap, "foo[1-3]", "foo[1-4]@tcp3")

    def testWrondConstructor(self):
        """should complain if a nodes is missing when instanciating"""
        self.assertRaises(InvalidNidMapError, NidMap, nodes_pat="foo[1-3]")
        self.assertRaises(InvalidNidMapError, NidMap, nids_pat="foo[1-3]")

    def testCheckException(self):
        """cast NidMap exception to string is ok"""
        exp = InvalidNidMapError("foo", "foo[1-2]")
        str(exp)

    def testFromList(self):
        """construct from a list of modelnidmap"""
        line1 = ModelNidMap()
        line1.parse("nodes=foo[1-2] nids=foo[1-2]-ib0@o2ib4")
        line2 = ModelNidMap()
        line2.parse("nodes=bar[1-2] nids=bar[1-2]-ib0@o2ib4")
        nm = NidMap.fromlist([line1, line2])
        self.assertEqual(nm["foo1"], ["foo1-ib0@o2ib4"])
        self.assertEqual(nm["foo2"], ["foo2-ib0@o2ib4"])
        self.assertEqual(nm["bar1"], ["bar1-ib0@o2ib4"])
        self.assertEqual(nm["bar2"], ["bar2-ib0@o2ib4"])

    def testMultipleNid(self):
        """add multiple nid per node"""
        nm = NidMap()
        nm.add("foo[4-5]", "foo[4-5]-ib0@o2ib1")
        nm.add("foo[4-5]", "foo[4-5]-ib1@o2ib2")
        self.assertEqual(nm["foo4"], ["foo4-ib0@o2ib1", "foo4-ib1@o2ib2"])
        self.assertEqual(nm["foo5"], ["foo5-ib0@o2ib1", "foo5-ib1@o2ib2"])
