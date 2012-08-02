#!/usr/bin/env python
# Shine.CLI.TextTable test suite
# Written by A. Degremont 2012-04-26
# $Id$

"""Unit test for TextTable"""

import unittest

from Shine.CLI.TextTable import TextTable

class TextTableTest(unittest.TestCase):

    def test_empty(self):
        """empty table"""
        tbl = TextTable("%foo")
        self.assertEqual(str(tbl), "FOO\n---")

    def test_simple(self):
        """simple row"""
        tbl = TextTable("%one")
        tbl.append({'one': 'foo'})
        self.assertEqual(str(tbl), "ONE\n---\nfoo")

    def test_several_lines(self):
        """list of rows"""
        tbl = TextTable("%one")
        tbl.append({'one': 'foo1'})
        tbl.append({'one': 'foo2'})
        tbl.append({'one': 'foo3'})
        self.assertEqual(str(tbl), "ONE\n---\nfoo1\nfoo2\nfoo3")

    def test_length(self):
        """table length"""
        tbl = TextTable()
        tbl.append({'one': 'foo1'})
        tbl.append({'one': 'foo3'})
        self.assertEqual(len(tbl), 2)

    def test_two_fields(self):
        """format with 2 fields"""
        tbl = TextTable("%one %two")
        tbl.append({'one': 'foo1', 'two':'bar1'})
        self.assertEqual(str(tbl),"ONE  TWO\n---  ---\nfoo1 bar1")

    def test_aliases(self):
        """format with label aliases"""
        tbl = TextTable("%o %t")
        tbl.aliases = {'o': 'one', 't':'two'}
        tbl.append({'one': 'foo1', 'two': 'bar1'})
        self.assertEqual(str(tbl),"ONE  TWO\n---  ---\nfoo1 bar1")

    def test_noheader(self):
        """output without header"""
        tbl = TextTable("%one")
        tbl.show_header = False
        tbl.append({'one': 'foo'})
        self.assertEqual(str(tbl), "foo")

    def test_header_label(self):
        """output with header label"""
        tbl = TextTable("%fsname")
        tbl.header_labels = {'fsname': 'filesystem'}
        tbl.append({'fsname': 'foo'})
        self.assertEqual(str(tbl), "FILESYSTEM\n----------\nfoo")
        
    def test_column_width_values(self):
        """column width with longer values"""
        tbl = TextTable("%one %two")
        tbl.append({'one': 'foo1', 'two': 'bar1'})
        tbl.append({'one': 'foofoo2', 'two': 'barbar2'})
        self.assertEqual(str(tbl), 
"""ONE     TWO
---     ---
foo1    bar1
foofoo2 barbar2""")

    def test_column_alignement_header(self):
        """column alignment with longer header"""
        tbl = TextTable("%filesystem %two")
        tbl.append({'filesystem': 'foo', 'two': 'bar'})
        self.assertEqual(str(tbl), 
                         "FILESYSTEM TWO\n---------- ---\nfoo        bar")

    def test_row_with_none_value(self):
        """row with a None value"""
        tbl = TextTable("%foo")
        tbl.append({'foo': None})
        self.assertEqual(str(tbl), "FOO\n---\n")

    def test_unknown_key(self):
        """unknown key should raise KeyError"""
        tbl = TextTable("%one is %nice")
        tbl.append({'one': 'bar'})
        self.assertRaises(KeyError, str, tbl)
        
    def test_ignore_bad_keys(self):
        """bad keys are displayed as-is."""
        tbl = TextTable("%one is %nice")
        tbl.ignore_bad_keys = True
        tbl.append({'one': 'bar'})
        self.assertEqual(str(tbl), "ONE IS %NICE\n--- -- -----\nbar is %nice")

    def test_special_character(self):
        """espace character for %"""
        tbl = TextTable("%one %%")
        tbl.append({'one': '34'})
        self.assertEqual(str(tbl), 'ONE %\n--- -\n34  %')

    def test_column_width_explicit(self):
        """force an explicit column width"""
        tbl = TextTable("%10one %two")
        tbl.append({'one': 'foo', 'two': 'bar'})
        self.assertEqual(str(tbl),
                         "ONE        TWO\n---        ---\nfoo        bar")

    def test_column_short(self):
        """force a too short column width which will truncate value"""
        tbl = TextTable("%4label %two")
        tbl.append({'label': 'lustre-OST0000', 'two': 'bar'})
        self.assertEqual(str(tbl), "L... TWO\n---- ---\nl... bar")

    def test_column_alignement_explicit(self):
        """force an explicit column width"""
        tbl = TextTable("%>10one %two")
        tbl.append({'one': 'foo', 'two': 'bar'})
        self.assertEqual(str(tbl), 
                         "       ONE TWO\n       --- ---\n       foo bar")

    def test_color(self):
        """display with color"""
        tbl = TextTable("%one")
        tbl.color = True
        tbl.append({'one': 'foo'})
        self.assertEqual(str(tbl), "\033[34mONE\033[0m\n---\nfoo")

    def test_title(self):
        """display with a simple title"""
        tbl = TextTable("%one")
        tbl.title = "test title"
        tbl.append({'one': 'foo'})
        self.assertEqual(str(tbl), " test title \nONE\n---\nfoo")

    def test_title_with_color(self):
        """display with title and color"""
        tbl = TextTable("%filesystem %two")
        tbl.title = "title"
        tbl.color = True
        tbl.append({'filesystem': 'foo', 'two': 'bar'})
        self.assertEqual(str(tbl), 
"""===\033[34m title \033[0m====
\033[34mFILESYSTEM TWO\033[0m
---------- ---
foo        bar""")

    def test_optional_colum_empty(self):
        """an empty optional column should not be displayed"""
        tbl = TextTable("%foo %bar")
        tbl.optional_cols = [ 'bar' ]
        tbl.append({'foo': 'zap', 'bar': None })
        self.assertEqual(str(tbl), """FOO\n---\nzap""")

    def test_optional_colum_non_empty(self):
        """an non-empty optional column shoud be displayed"""
        tbl = TextTable("%foo %bar")
        tbl.optional_cols = [ 'bar' ]
        tbl.append({'foo': 'zap', 'bar': 'zop' })
        self.assertEqual(str(tbl), """FOO BAR\n--- ---\nzap zop""")

    def test_pattern_fields(self):
        """fields could be extracted from pattern"""
        tbl = TextTable("%foo %bar")
        self.assertEqual(['foo', 'bar'], tbl.pattern_fields())

        tbl = TextTable("%foo likes %>20bar and %other")
        self.assertEqual(['foo', 'bar', 'other'], tbl.pattern_fields())
