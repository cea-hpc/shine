#!/usr/bin/env python
# Shine.Lustre.Component test suite
# Written by A. Degremont 2011-01-19


"""Unit test for Component"""

import unittest

from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Server import Server
from Shine.Lustre.Component import ComponentGroup, Component, MOUNTED, OFFLINE
from Shine.Lustre.Target import Target

class ComponentGroupTest(unittest.TestCase):

    def testGenericComponent(self):
        """test ComponentGroup simple methods"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        self.assertEqual(len(grp), 0)
        comp = Component(fs, Server('foo', ['foo@tcp']))
        comp.TYPE = 'A'

        # add()
        grp.add(comp)
        # __len__
        self.assertEqual(len(grp), 1)
        # __str__
        self.assertEqual(str(grp), 'comp-A')
        # __getitem__
        self.assertEqual(grp[comp.uniqueid()], comp)
        # __contains__
        self.assertTrue(comp in grp)
        # __iter__
        self.assertEqual(list(iter(grp)), [ comp ])
        # Could not add() twice the same component
        try:
            grp.add(comp)
        except KeyError as error:
            txt = "'A component with id comp-A-foo@tcp already exists.'"
            self.assertEqual(str(error), txt)

    def testServers(self):
        """test ComponentGroup.servers()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        grp.add(Component(fs, Server('foo1', ['foo1@tcp'])))
        grp.add(Component(fs, Server('foo2', ['foo2@tcp'])))
        self.assertEqual(str(grp.servers()), "foo[1-2]")

    def testAllServers(self):
        """test ComponentGroup.allservers()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        grp.add(Target(fs, Server('foo1', ['foo1@tcp']), 0, '/dev/sda'))
        comp = Target(fs, Server('foo2', ['foo2@tcp']), 1, '/dev/sda')
        grp.add(comp)
        comp.add_server(Server('foo3', ['foo3@tcp0']))
        self.assertEqual(str(grp.allservers()), "foo[1-3]")

    def testLabels(self):
        """test ComponentGroup.labels()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        comp = Component(fs, Server('foo1', ['foo1@tcp']))
        comp.TYPE = 'A'
        grp.add(comp)
        comp = Component(fs, Server('foo2', ['foo2@tcp']))
        comp.TYPE = 'B'
        grp.add(comp)
        self.assertEqual(str(grp.labels()), 'comp-A,comp-B')

    def testUpdate(self):
        """test ComponentGroup.update()"""
        fs = FileSystem('comp')
        grp1 = ComponentGroup()
        comp1 = Component(fs, Server('foo1', ['foo1@tcp']))
        grp1.add(comp1)
        grp2 = ComponentGroup()
        comp2 = Component(fs, Server('foo2', ['foo2@tcp']))
        grp2.add(comp2)
        grp1.update(grp2)
        self.assertEqual(len(grp1), 2)
        self.assertTrue(comp1 in grp1)
        self.assertTrue(comp2 in grp1)

    def testOr(self):
        """test ComponentGroup.__or__()"""
        fs = FileSystem('comp')
        grp1 = ComponentGroup()
        comp1 = Component(fs, Server('foo1', ['foo1@tcp']))
        grp1.add(comp1)
        grp2 = ComponentGroup()
        comp2 = Component(fs, Server('foo2', ['foo2@tcp']))
        grp2.add(comp2)
        merge = grp1|grp2
        self.assertEqual(len(merge), 2)
        self.assertTrue(comp1 in merge)
        self.assertTrue(comp2 in merge)

    def testFilterKey(self):
        """test ComponentGroup.filter(key)"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        comp1 = Component(fs, Server('foo1', ['foo1@tcp']))
        comp1.state = MOUNTED
        grp.add(comp1)
        comp2 = Component(fs, Server('foo2', ['foo2@tcp']))
        comp2.state = OFFLINE
        grp.add(comp2)
        comp3 = Component(fs, Server('foo3', ['foo3@tcp']))
        comp3.state = MOUNTED
        grp.add(comp3)
        comp4 = Component(fs, Server('foo4', ['foo4@tcp']))
        comp4.state = OFFLINE
        grp.add(comp4)
        offgrp = grp.filter(key=lambda comp: comp.state == OFFLINE)
        self.assertEqual(len(offgrp), 2)
        self.assertTrue(comp2 in offgrp)
        self.assertTrue(comp4 in offgrp)

    def testFilterSupports(self):
        """test ComponentGroup.filter(supports and key)"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        comp1 = Component(fs, Server('foo1', ['foo1@tcp']))
        comp1.state = MOUNTED
        grp.add(comp1)
        comp2 = Component(fs, Server('foo2', ['foo2@tcp']))
        comp2.state = OFFLINE
        grp.add(comp2)
        comp3 = Component(fs, Server('foo3', ['foo3@tcp']))
        comp3.state = MOUNTED
        grp.add(comp3)
        comp4 = Component(fs, Server('foo4', ['foo4@tcp']))
        comp4.state = OFFLINE
        grp.add(comp4)
        offgrp = grp.filter(supports='is_external', key=lambda comp: comp.state == OFFLINE)
        self.assertEqual(len(offgrp), 2)
        self.assertTrue(comp2 in offgrp)
        self.assertTrue(comp4 in offgrp)

    def testEnabled(self):
        """test ComponentGroup.enabled()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        comp1 = Component(fs, Server('foo1', ['foo1@tcp']), enabled=False)
        grp.add(comp1)
        comp2 = Component(fs, Server('foo2', ['foo2@tcp']))
        grp.add(comp2)
        comp3 = Component(fs, Server('foo3', ['foo3@tcp']), enabled=False)
        grp.add(comp3)
        comp4 = Component(fs, Server('foo4', ['foo4@tcp']))
        grp.add(comp4)
        offgrp = grp.enabled()
        self.assertEqual(len(offgrp), 2)
        self.assertTrue(comp2 in offgrp)
        self.assertTrue(comp4 in offgrp)

    def testManaged(self):
        """test ComponentGroup.managed()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        comp1 = Component(fs, Server('foo1', ['foo1@tcp']), mode="external")
        grp.add(comp1)
        comp2 = Component(fs, Server('foo2', ['foo2@tcp']))
        grp.add(comp2)
        comp3 = Component(fs, Server('foo3', ['foo3@tcp']), enabled=False)
        grp.add(comp3)
        comp4 = Component(fs, Server('foo4', ['foo4@tcp']))
        grp.add(comp4)
        offgrp = grp.managed()
        self.assertEqual(len(offgrp), 2)
        self.assertTrue(comp2 in offgrp)
        self.assertTrue(comp4 in offgrp)

    def testGroupBy(self):
        """test ComponentGroup.groupby()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        comp1 = Component(fs, Server('foo1', ['foo1@tcp']), mode="external")
        grp.add(comp1)
        comp2 = Component(fs, Server('foo2', ['foo2@tcp']))
        grp.add(comp2)
        comp3 = Component(fs, Server('foo3', ['foo3@tcp']), mode="external")
        grp.add(comp3)
        comp4 = Component(fs, Server('foo4', ['foo4@tcp']))
        grp.add(comp4)
        results = [[mode, list(comps)] for mode, comps in grp.groupby(attr='_mode')]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "external")
        self.assertTrue(comp1 in results[0][1])
        self.assertTrue(comp3 in results[0][1])
        self.assertEqual(results[1][0], "managed")
        self.assertTrue(comp2 in results[1][1])
        self.assertTrue(comp4 in results[1][1])

    def testGroupByServer(self):
        """test ComponentGroup.groupbyserver()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        srv1 = Server('foo1', ['foo1@tcp'])
        srv2 = Server('foo2', ['foo2@tcp'])
        comp1 = Component(fs, srv1)
        comp1.TYPE = 'A'
        grp.add(comp1)
        comp2 = Component(fs, srv2)
        comp2.TYPE = 'B'
        grp.add(comp2)
        comp3 = Component(fs, srv1)
        comp3.TYPE = 'C'
        grp.add(comp3)
        comp4 = Component(fs, srv2)
        comp4.TYPE = 'D'
        grp.add(comp4)
        key = lambda c: c.TYPE
        results = [[srv, sorted(comps, key=key)] for srv, comps in grp.groupbyserver()]
        self.assertEqual(len(results), 2)
        self.assertTrue([srv1, [comp1, comp3]] in results)
        self.assertTrue([srv2, [comp2, comp4]] in results)

    def test_group_by_all_servers(self):
        """test ComponentGroup.groupbyallservers()"""
        fs = FileSystem('comp')
        grp = ComponentGroup()
        srv1 = Server('foo1', ['foo1@tcp'])
        srv2 = Server('foo2', ['foo2@tcp'])
        comp1 = Target(fs, srv1, 0, '/dev/sda')
        comp1.add_server(srv2)
        grp.add(comp1)
        comp2 = Target(fs, srv2, 1, '/dev/sdb')
        comp2.add_server(srv1)
        grp.add(comp2)
        comp3 = Target(fs, srv1, 2, '/dev/sdc')
        comp3.add_server(srv2)
        grp.add(comp3)
        comp4 = Target(fs, srv2, 3, '/dev/sdd')
        comp4.add_server(srv1)
        grp.add(comp4)
        key = lambda c: c.TYPE
        results = [[srv, sorted(comps, key=key)] for srv, comps in grp.groupbyallservers()]
        self.assertEqual(len(results), 2)
        self.assertTrue([srv1, [comp1, comp2, comp3, comp4]] in results)
        self.assertTrue([srv2, [comp1, comp2, comp3, comp4]] in results)

    def test_managed_active(self):
        """test ComponentGroup.managed() with active option"""
        fs = FileSystem('active')
        grp = ComponentGroup()
        srv = Server('foo1', ['foo1@tcp'])
        comp1 = Component(fs, srv)
        comp1.TYPE = 'A'
        grp.add(comp1)
        comp2 = Component(fs, srv, active='no')
        comp2.TYPE = 'B'
        grp.add(comp2)
        comp3 = Component(fs, srv, active='nocreate')
        comp3.TYPE = 'C'
        grp.add(comp3)
        comp4 = Component(fs, srv, active='no', mode='external')
        comp4.TYPE = 'D'
        grp.add(comp4)
        self.assertEqual(str(grp.managed()), 'active-A,active-C')
        self.assertEqual(str(grp.managed(inactive=True)),
                         'active-A,active-B,active-C,active-D')
