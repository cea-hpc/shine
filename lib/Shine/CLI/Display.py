# Display.py -- Display filesystem state in text mode.
# Copyright (C) 2012 CEA
#
# This file is part of shine
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# $Id$

"""
Helping method to format filesystem state for text output.
"""

import sys
from operator import attrgetter

from Shine.CLI.TextTable import TextTable

from Shine.Lustre.Component import Component
from Shine.Lustre.Target import Target

class DisplayError(Exception):
    """An error prevent display to be done correctly."""

(KILO, MEGA, GIGA, TERA) = (1024.0, 1024.0 ** 2, 1024.0 ** 3, 1024.0 ** 4)

def _human_unit(value):
    """
    Format numerical ``value'' to display it using human readable unit like
    (KB, MB, GB, ...).
    """
    if value >= TERA:
        fmt = "%.1fTB" % (value / TERA)
    elif value >= GIGA:
        fmt = "%.1fGB" % (value / GIGA)
    elif value >= MEGA:
        fmt = "%.1fMB" % (value / MEGA)
    elif value >= KILO:
        fmt = "%.1fKB" % (value / KILO)
    else:
        fmt = "%d" % value
    return fmt


COMP_FIELDS = {

        'fsname':  { 'supports': 'fs', 'getter': lambda comp: comp.fs.fs_name },
        'label':   { 'supports': 'label', 'getter': attrgetter('label') },
        'node':    { 'supports': 'server',
                     'getter': lambda comp: str(comp.server.hostname) },
        'servers': { 'supports': 'allservers',
                     'getter': lambda comp: str(comp.allservers().nodeset()) },
        'status':  { 'supports': 'text_status',
                     'getter': lambda comp: comp.text_status() },
        'type':    { 'supports': 'TYPE',
                     'getter': lambda comp: comp.TYPE.upper()[0:3] },

        # Target specific fields
        'device':  { 'supports': 'dev', 'getter': attrgetter('dev') },
        'flags':   { 'supports': 'flags',
                     'getter': lambda tgt: ' '.join(tgt.flags()) },
        'hanodes': { 'supports': 'failservers',
                     'getter': lambda tgt: str(tgt.failservers.nodeset()) },
        'index':   { 'supports': 'index',
                     'getter': lambda tgt: str(tgt.index) },
        'jdev':    { 'supports': 'journal',
                     'getter': lambda tgt: tgt.journal and tgt.journal.dev },
        'jsize':   { 'supports': 'journal',
                     'getter': lambda tgt: tgt.journal and \
                                           _human_unit(tgt.journal.dev_size) },
        'network': { 'supports': 'network', 'getter': attrgetter('network') },
        'size':    { 'supports': 'dev_size',
                     'getter': lambda tgt: _human_unit(tgt.dev_size) },
        'tag':     { 'supports': 'tag', 'getter': attrgetter('tag') },
        'target':  { 'supports': 'get_id', 'getter': Target.get_id },

        # Client specific fields
        'mntpath': { 'supports': 'mount_path',
                     'getter': attrgetter('mount_path') },
        'mntopts': { 'supports': 'mount_options',
                     'getter': attrgetter('mount_options') },

    }

def _get_fields(comp, fields):
    """
    Build a dict, with keys taken from ``fields'' and values based on
    COMP_FIELDS definition, for the provided Component ``comp''.

    Raise DisplayError if fields contains an unknown field.
    """
    d_fields = {}
    for field in fields:
        if field not in COMP_FIELDS:
            raise DisplayError("bad field name '%%%s'" % field)
        if comp.capable(COMP_FIELDS[field]['supports']):
            d_fields[field] = COMP_FIELDS[field]['getter'](comp)
        else:
            d_fields[field] = '-'
    return d_fields

def table_fill(tbl, fs, sort_key=None, supports=None):
    """
    Fill ``tbl'' with the component properties from filesystem ``fs''.

    Apply a sorting based on ``sort_key'' if provided.

    This is applied only to component supporting ``supports'' if provided.
    """

    # Build the list of all fields used in the display format, except the
    # special group fields.
    pat_fields = tbl.pattern_fields()
    for elem in ('count', 'labels', 'nodes'):
        if elem in pat_fields:
            pat_fields.remove(elem)

    # Grouped by visible fields
    def fieldvals(comp):
        """Get the value list of field for ``comp''."""
        return _get_fields(comp, pat_fields).values()
    grplst = [ (list(compgrp)[0], compgrp) for _, compgrp in \
               fs.components.managed(supports=supports).groupby(key=fieldvals) ]

    # Sort
    def sorter((first, _)):
        """
        Sort grplist based on provided sort_key for the first element of
        compgrp.
        """
        if sort_key is None:
            return None
        return sort_key(first)

    for first, compgrp in sorted(grplst, key=sorter):

        # Get component fields
        fields = _get_fields(first, pat_fields)

        # Get ComponentGroup fields
        fields['count'] = str(len(compgrp))
        fields['labels'] = str(compgrp.labels())
        fields['nodes'] = str(compgrp.servers())
        tbl.append(fields)


def setup_table(options, fmt=None):
    """
    Return a TextTable already setup based on display command line options like
    color and header.
    """
    tbl = TextTable(fmt)
    tbl.color = (sys.stdout.isatty() and options.color == 'auto') or \
                (options.color == 'always')
    tbl.show_header = options.header
    return tbl

def display(cmd, fs, supports=None):
    """
    Display the components from filesystem ``fs'' in a text table.

    This takes in account command line options like Views or custom format.
    It also toggles the color display based on options or if stdout is a tty.
    """

    view = cmd.options.view

    tbl = setup_table(cmd.options)

    key = None

    #
    # Custom format
    #
    if cmd.options.viewfmt:
        tbl.title = "FILESYSTEM STATUS (%s)" % fs.fs_name
        tbl.fmt = cmd.options.viewfmt
        key = lambda t: (t.DISPLAY_ORDER, t.label)

    #
    # Predefined views
    #
    elif view == "fs":
        # Note: This uses "managed()", but before it was "enabled()"!
        tbl.title = "FILESYSTEM STATUS (%s)" % fs.fs_name
        tbl.fmt = "%type %>count %status %nodes"
        tbl.header_labels = {'count': '#'}
        key = lambda t: (t.DISPLAY_ORDER, t.text_status())

    elif view == "target":
        # Display each targets (component which support an index), sorted by
        # display order and index
        tbl.title = "FILESYSTEM TARGETS (%s)" % fs.fs_name
        tbl.fmt = "%target %type %>index %servers %device %status"
        tbl.header_labels = {'index': 'idx'}
        key = lambda t: (t.DISPLAY_ORDER, t.label)
        if not supports:
            supports = "index"

    elif view == "disk":
        tbl.title = "FILESYSTEM DISKS (%s)" % fs.fs_name
        tbl.fmt = "%device %servers %>size %>jdev %type %>index %tag %label " \
                  "%flags %fsname %status"
        tbl.header_labels = { 'size': 'dev_size', 'jdev': 'journal_device'}
        tbl.optional_cols = ['jdev', 'tag']
        key = lambda t: (t.DISPLAY_ORDER, t.label)
        if not supports:
            supports = "dev"

    table_fill(tbl, fs, sort_key=key, supports=supports)
    return str(tbl)
