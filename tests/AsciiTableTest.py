#!/usr/bin/env python
# Shine.Configuration.Model test suite
# Written by S. Thiell 2010-02-12
# $Id$


"""Unit test for AsciiTable"""

import os
import sys
import unittest
import tempfile

sys.path.insert(0, '../lib')

import Shine.Utilities.AsciiTable as AsciiTable


class AsciiTableTest(unittest.TestCase):


    outputAsciiTableHeader = """+------------------------------------------+------------------------------------------+------------------------------------------+
|first Key                                 |second Key                                |third Key                                 |
+------------------------------------------+------------------------------------------+------------------------------------------
|value11value11value11value11value11value1 |value12value12value12                     |value13                                   |
|+1value11value11                          |                                          |                                          |
|value21                                   |value22value22value22value22value22value2 |value23                                   |
|                                          |+2value22value22value22value22value22value|                                          |
|                                          |+22value22value22value22value22           |                                          |
|value31                                   |value32value32value32value32value32value3 |value33value33value33value33value33value3 |
|                                          |+2value32value32                          |+3value33value33value33value33value33value|
|                                          |                                          |+33value33value33                         |
+------------------------------------------+------------------------------------------+------------------------------------------+
"""

    outputAsciiTableNoHeader = """+------------------------------------------+------------------------------------------+------------------------------------------+
|value11value11value11value11value11value1 |value12value12value12                     |value13                                   |
|+1value11value11                          |                                          |                                          |
|value21                                   |value22value22value22value22value22value2 |value23                                   |
|                                          |+2value22value22value22value22value22value|                                          |
|                                          |+22value22value22value22value22           |                                          |
|value31                                   |value32value32value32value32value32value3 |value33value33value33value33value33value3 |
|                                          |+2value32value32                          |+3value33value33value33value33value33value|
|                                          |                                          |+33value33value33                         |
+------------------------------------------+------------------------------------------+------------------------------------------+
"""

    def testSimple(self):
        """test simple layout"""
        layout = AsciiTable.AsciiTableLayout()
        layout.set_show_header(False)
        layout.set_column("key1", 0, AsciiTable.AsciiTableLayout.LEFT, "first Key")
        layout.set_column("key2", 1, AsciiTable.AsciiTableLayout.LEFT, "second Key")

        f = tempfile.NamedTemporaryFile()
        AsciiTable.AsciiTable.get_term_cols = AsciiTable.AsciiTable.get_term_cols_from_environ
        table = AsciiTable.AsciiTable(f)
        os.environ['COLUMNS'] = "119"
        rows = []
        rows.append({ "key1" : "blah blah", "key2": "/some/dev/thing" })
        rows.append({ "key1" : "value", "key2": "oth er th ing" })
        table.print_from_list_of_dict(rows, layout)
        f.seek(0)
        self.assertEqual(f.read(), """+----------+----------------+
|blah blah |/some/dev/thing |
|value     |oth er th ing   |
+----------+----------------+
""")
        f.close()

    def testEmpty(self):
        """test empty ascii table"""
        layout = AsciiTable.AsciiTableLayout()
        layout.set_show_header(False)
        layout.set_column("key1", 0, AsciiTable.AsciiTableLayout.LEFT, "first Key")
        layout.set_column("key2", 1, AsciiTable.AsciiTableLayout.LEFT, "second Key")
        layout.set_column("key3", 1, AsciiTable.AsciiTableLayout.LEFT, "third Key")

        f = tempfile.NamedTemporaryFile()
        AsciiTable.AsciiTable.get_term_cols = AsciiTable.AsciiTable.get_term_cols_from_environ
        table = AsciiTable.AsciiTable(f)
        os.environ['COLUMNS'] = "119"
        rows = []
        rows.append({ "key1" : "", "key2": "", "key3": "" })
        rows.append({ "key1" : "", "key2": "", "key3": ""  })
        table.print_from_list_of_dict(rows, layout)
        f.seek(0)
        self.assertEqual(f.read(), """+----------+----------+
|          |          |
|          |          |
+----------+----------+
""")
        f.close()

    def runTestAsciiTable(self, show_header, expected):
        """run test ascii table"""
        layout = AsciiTable.AsciiTableLayout()
        layout.set_show_header(show_header)
        layout.set_column("key1", 0, AsciiTable.AsciiTableLayout.LEFT, "first Key")
        layout.set_column("key2", 1, AsciiTable.AsciiTableLayout.LEFT, "second Key")
        layout.set_column("key3", 2, AsciiTable.AsciiTableLayout.LEFT, "third Key")

        f = tempfile.NamedTemporaryFile()
        AsciiTable.AsciiTable.get_term_cols = AsciiTable.AsciiTable.get_term_cols_from_environ
        table = AsciiTable.AsciiTable(f)
        os.environ['COLUMNS'] = "129"
        simple1 = { "key1" : "value11" * 8, "key2": "value12" * 3, "key3": "value13" }
        simple2 = { "key1" : "value21", "key2": "value22" * 16, "key3": "value23"  }
        simple3 = { "key1" : "value31", "key2": "value32" * 8, "key3": "value33" * 14 }
        rows = [ simple1, simple2, simple3 ]
        table.print_from_list_of_dict(rows, layout)
        f.seek(0)
        self.assertEqual(f.read(), expected)
        f.close()

    def testAsciiTableNoHeader(self):
        """test ascii table with header"""
        self.runTestAsciiTable(True, self.outputAsciiTableHeader)

    def testAsciiTableHeader(self):
        """test ascii table without header"""
        self.runTestAsciiTable(False, self.outputAsciiTableNoHeader)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(AsciiTableTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
