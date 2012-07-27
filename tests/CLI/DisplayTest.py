#!/usr/bin/env python
# Shine.CLI.TextTable test suite
# Written by A. Degremont 2012-07-04
# $Id$

"""Unit test for CLI.Display"""

import unittest

import sys
from Shine.CLI.TextTable import TextTable
from Shine.CLI.Display import setup_table, table_fill, display, DisplayError

from Shine.Lustre.FileSystem import FileSystem, Server

class DummyCommand(object):
    """Command mock-up for test purpose only."""
    def __init__(self, options):
        self.options = options

class DummyOptions(object):
    """OptionParser option mock-up for test purpose only."""
    def __init__(self, color, header, view='fs', fmt=None):
        self.color = color
        self.header = header
        self.view = view
        self.viewfmt = fmt

class FakeFile(object):
    """Mockup to control how a File like object claims it is a tty or not."""
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty

class SetupTableTest(unittest.TestCase):

    def setUp(self):
        self._stdout = sys.stdout

    def tearDown(self):
        sys.stdout = self._stdout

    def test_show_headers(self):
        """setup of show_header"""
        tbl = setup_table(DummyOptions('auto', True))
        self.assertTrue(tbl.show_header)
        tbl = setup_table(DummyOptions('auto', False))
        self.assertFalse(tbl.show_header)

    def test_notty(self):
        """setup with no tty attached"""
        sys.stdout = FakeFile(False)

        tbl = setup_table(DummyOptions('always', True))
        self.assertTrue(tbl.color)
        tbl = setup_table(DummyOptions('never', True))
        self.assertFalse(tbl.color)
        tbl = setup_table(DummyOptions('auto', True))
        self.assertFalse(tbl.color)

    def test_tty(self):
        """setup with a fake tty attached"""
        sys.stdout = FakeFile(True)

        tbl = setup_table(DummyOptions('always', True))
        self.assertTrue(tbl.color)
        tbl = setup_table(DummyOptions('never', True))
        self.assertFalse(tbl.color)
        tbl = setup_table(DummyOptions('auto', True))
        self.assertTrue(tbl.color)

class SimpleFillTests(unittest.TestCase):

    def setUp(self):
        self._fs = FileSystem('foofs')

    def _fmt_str(self, fmt, txt):
        tbl = TextTable(fmt)
        tbl.show_header = False
        table_fill(tbl, self._fs)
        self.assertEqual(str(tbl), txt)

    def test_empty_fs(self):
        """fill with an empty filesystem"""
        tbl = TextTable()
        table_fill(tbl, self._fs, None)
        self.assertEqual(len(tbl), 0)

    def test_bad_field(self):
        """fill with bad field name"""
        self._fs.new_target(Server('foo', ['foo@tcp']), 'mgt', 0, '/dev/foo')
        tbl = TextTable('%badname')
        self.assertRaises(DisplayError, table_fill, tbl, self._fs)

    def test_missing_field(self):
        """fill with an irrelevant field"""
        self._fs.new_router(Server('foo', ['foo@tcp']))
        self._fmt_str('%index', '-')

    def test_simple_fs(self):
        """fill with a MGT only filesystem"""
        self._fs.new_target(Server('foo', ['foo@tcp']), 'mgt', 0, '/dev/foo')
        self._fmt_str("%fsname %node", 'foofs  foo')

    def test_simple_fs_group_fields(self):
        """fill with a MGT only filesystem with group fields"""
        self._fs.new_target(Server('foo', ['foo@tcp']), 'mgt', 0, '/dev/foo')
        self._fmt_str("%fsname %node %count %labels %nodes",
                      'foofs  foo  1     MGS    foo')

    def test_common_fields(self):
        """fill with component common fields"""
        self._fs.new_target(Server('foo', ['foo@tcp']), 'mgt', 0, '/dev/foo')
        self._fmt_str("%fsname %label %node %status %type %servers",
                      'foofs  MGS   foo  unknown MGT  foo')

    def test_target_fields(self):
        """fill with target fields"""
        tgt = self._fs.new_target(Server('foo', ['foo@tcp']), 'mgt', 0,
                                  '/dev/foo', '/dev/jfoo', tag='footag',
                                  network="tcp")
        tgt.add_server(Server('foo2', ['foo2@tcp']))
        tgt.journal.dev_size = 123

        fmt = "%device %2flags %hanodes %1index %jdev %3jsize"
        self._fmt_str(fmt, '/dev/foo    foo2    0 /dev/jfoo 123')

        fmt = "%3network %tag %servers"
        self._fmt_str(fmt, 'tcp footag foo,foo2')

    def test_size_field(self):
        """fill with different dev size"""
        tgt = self._fs.new_target(Server('foo', ['foo@tcp']), 'mgt', 0,
                                  '/dev/foo')
        tgt.dev_size = 123
        self._fmt_str('%size', '123')
        # KB
        tgt.dev_size = 123456
        self._fmt_str('%size', '120.6KB')
        # MB
        tgt.dev_size = 123456789
        self._fmt_str('%size', '117.7MB')
        # GB
        tgt.dev_size = 12345678901
        self._fmt_str('%size', '11.5GB')
        # TB
        tgt.dev_size = 1024**4
        self._fmt_str('%size', '1.0TB')

    def test_journal_fields(self):
        """fill using journal fields with no journal"""
        self._fs.new_target(Server('foo', ['foo@tcp']), 'mgt', 0, '/dev/foo')
        self._fmt_str("%jdev %jsize", '')

    def test_client_fields(self):
        """fill with client fields"""
        self._fs.new_client(Server('foo', ['foo@tcp']), '/mnt/foo', 'ro')
        self._fmt_str("%mntpath %mntopts", '/mnt/foo ro')

class ComplexFillTests(unittest.TestCase):

    def setUp(self):
        self._fs = FileSystem('complex')
        # Router (foo0)
        self._fs.new_router(Server('foo0', ['foo0@tcp']))
        # MGS (foo1)
        self._fs.new_target(Server('foo1', ['foo1@tcp']), 'mgt', 0, '/dev/mgt')
        # OSTs (foo3)
        srv3 = Server('foo3', ['foo3@tcp'])
        self._fs.new_target(srv3, 'ost', 0, '/dev/ost0')
        self._fs.new_target(srv3, 'ost', 1, '/dev/ost1')
        # MDT (foo2)
        self._fs.new_target(Server('foo2', ['foo2@tcp']), 'mdt', 0, '/dev/mdt')

    def test_sorting(self):
        """fill with 2 different sortings"""
        tbl = TextTable(fmt="%4fsname %node")
        tbl.show_header = False
        key = lambda t: t.TYPE
        table_fill(tbl, self._fs, key)
        self.assertEqual(str(tbl), 'c... foo2\nc... foo1\nc... foo3\nc... foo0')

        tbl = TextTable(fmt="%4fsname %node")
        tbl.show_header = False
        key = lambda t: t.DISPLAY_ORDER
        table_fill(tbl, self._fs, key)
        self.assertEqual(str(tbl), 'c... foo0\nc... foo1\nc... foo2\nc... foo3')

    def test_format_group(self):
        """fill with group field in format"""
        tbl = TextTable(fmt="%3type %count")
        tbl.show_header = False
        table_fill(tbl, self._fs)
        self.assertEqual(str(tbl), 'MDT 1\nMGT 1\nOST 2\nROU 1')

    def test_support(self):
        """fill with a support filter"""
        tbl = TextTable(fmt="%3type %node %count")
        tbl.show_header = False
        table_fill(tbl, self._fs, None, supports='dev')
        self.assertEqual(str(tbl), 'MGT foo1 1\nMDT foo2 1\nOST foo3 2')


class DisplayTest(unittest.TestCase):

    def setUp(self):
        self._fs = FileSystem('display')
        # Router (foo0)
        self._fs.new_router(Server('foo0', ['foo0@tcp']))
        # MGS (foo1)
        self._fs.new_target(Server('foo1', ['foo1@tcp']), 'mgt', 0, '/dev/mgt')
        # OSTs (foo3)
        srv3 = Server('foo3', ['foo3@tcp'])
        self._fs.new_target(srv3, 'ost', 0, '/dev/ost0')
        self._fs.new_target(srv3, 'ost', 1, '/dev/ost1')
        # MDT (foo2)
        self._fs.new_target(Server('foo2', ['foo2@tcp']), 'mdt', 0, '/dev/mdt')

    def test_view_custom(self):
        """display with a custom format"""
        opts = DummyOptions(color='never', header=True, fmt='%type %node')
        cmd = DummyCommand(opts)
        txt = display(cmd, self._fs)
        self.assertEqual(txt, """ FILESYSTEM STATUS (display) 
TYPE NODE
---- ----
ROU  foo0
MGT  foo1
MDT  foo2
OST  foo3""")

    def test_view_fs(self):
        """display with fs view"""
        opts = DummyOptions(color='never', header=True, view='fs', fmt=None)
        cmd = DummyCommand(opts)
        txt = display(cmd, self._fs)
        self.assertEqual(txt, """ FILESYSTEM STATUS (display) 
TYPE # STATUS  NODES
---- - ------  -----
ROU  1 unknown foo0
MGT  1 unknown foo1
MDT  1 unknown foo2
OST  2 unknown foo3""")

    def test_view_target(self):
        """display with target view"""
        opts = DummyOptions(color='never', header=True, view='target')
        cmd = DummyCommand(opts)
        txt = display(cmd, self._fs)
        self.assertEqual(txt,
"""========== FILESYSTEM TARGETS (display) ==========
TARGET          TYPE IDX SERVERS DEVICE    STATUS
------          ---- --- ------- ------    ------
MGS             MGT    0 foo1    /dev/mgt  unknown
display-MDT0000 MDT    0 foo2    /dev/mdt  unknown
display-OST0000 OST    0 foo3    /dev/ost0 unknown
display-OST0001 OST    1 foo3    /dev/ost1 unknown""")

    def test_view_disk(self):
        """display with disk view"""
        opts = DummyOptions(color='never', header=True, view='disk')
        cmd = DummyCommand(opts)
        txt = display(cmd, self._fs)
        self.assertEqual(txt, """======================== FILESYSTEM DISKS (display) =========================
DEVICE    SERVERS DEV_SIZE  TYPE INDEX  LABEL           FLAGS FSNAME  STATUS
------    ------- --------  ---- -----  -----           ----- ------  ------
/dev/mgt  foo1           0  MGT      0  MGS                   display unknown
/dev/mdt  foo2           0  MDT      0  display-MDT0000       display unknown
/dev/ost0 foo3           0  OST      0  display-OST0000       display unknown
/dev/ost1 foo3           0  OST      1  display-OST0001       display unknown"""
                        )

    def test_color(self):
        """display with fs view and colors"""
        opts = DummyOptions(color='always', header=True, view='fs')
        cmd = DummyCommand(opts)
        txt = display(cmd, self._fs)
        self.assertEqual(txt, """\x1b[34m FILESYSTEM STATUS (display) \x1b[0m
\x1b[34mTYPE # STATUS  NODES\x1b[0m
---- - ------  -----
ROU  1 unknown foo0
MGT  1 unknown foo1
MDT  1 unknown foo2
OST  2 unknown foo3""")
