# Display.py -- Display filesystem state in text mode.
# Copyright (C) 2012-2014 CEA
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

"""
Helping method to format filesystem state for text output.
"""

import sys
from operator import attrgetter

from Shine.Configuration.Globals import Globals

from Shine.CLI.TextTable import TextTable

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
        'primary': { 'supports': 'defaultserver',
                     'getter': lambda comp: str(comp.defaultserver.hostname) },
        'node':    { 'supports': 'server',
                     'getter': lambda comp: str(comp.server.hostname) },
        'servers': { 'supports': 'allservers',
                     'getter': lambda comp: str(comp.allservers().nodeset()) },
        'status':  { 'supports': 'text_status',
                     'getter': lambda comp: comp.text_status() },
        'statusonly': { 'supports': 'text_status',
                     'getter': lambda comp: comp.text_statusonly() },
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
        'target':  { 'supports': 'get_id', 'getter': lambda tgt: tgt.get_id() },

        # Client specific fields
        'mntpath': { 'supports': 'mount_path',
                     'getter': attrgetter('mount_path') },
        'mntopts': { 'supports': 'mount_options',
                     'getter': attrgetter('mount_options') },
        'subdir':  { 'supports': 'subdir',
                     'getter': attrgetter('subdir') },

    }

def map_field(comp, field, dash=True):
    """
    Map a field name to a component value, based on rules from COMP_FIELD.

    Mapping, for a known but unsupported field for `comp', depends on `dash' value.
    If dash is true, '-' is returned, otherwise an empty string is returned.

    Raise DisplayError if field does not exist in COMP_FIELD.
    """
    if field not in COMP_FIELDS:
        raise DisplayError("bad field name '%%%s'" % field)

    if comp.capable(COMP_FIELDS[field]['supports']):
        return COMP_FIELDS[field]['getter'](comp)
    elif dash:
        return '-'
    else:
        return ''

def _get_fields(comp, fields):
    """
    Build a dict, with keys taken from ``fields'' and values based on
    COMP_FIELDS definition, for the provided Component ``comp''.

    Raise DisplayError if fields contains an unknown field.
    """
    d_fields = {}
    for field in fields:
        d_fields[field] = map_field(comp, field)
    return d_fields


def table_fill(tbl, fs, sort_key=None, supports=None, viewsupports=None):
    """
    Fill ``tbl'' with the component properties from filesystem ``fs''.

    Apply a sorting based on ``sort_key'' if provided.

    This is applied only to component supporting ``supports'' if provided.
    """

    # Build the list of all fields used in the display format, except the
    # special group fields.
    pat_fields = set(tbl.pattern_fields())
    grp_fields = pat_fields & set(('count', 'labels', 'nodes'))
    pat_fields.difference_update(grp_fields)

    # Grouped by visible fields
    comps = fs.components.managed(supports=supports, inactive=True)
    if viewsupports is not None:
        comps = comps.filter(supports=viewsupports)
    def fieldvals(comp):
        """Get the value list of field for ``comp''."""
        return list(_get_fields(comp, pat_fields).values())
    grplst = [ (list(compgrp)[0], compgrp) for _, compgrp in \
               comps.groupby(key=fieldvals) ]

    # Sort
    if sort_key is not None:
        grplst.sort(key=lambda group: sort_key(group[0]))

    for first, compgrp in grplst:

        # Get component fields
        fields = _get_fields(first, pat_fields)

        # Get ComponentGroup fields
        if 'count' in grp_fields:
            fields['count'] = str(len(compgrp))
        if 'labels' in grp_fields:
            fields['labels'] = str(compgrp.labels())
        if 'nodes' in grp_fields:
            fields['nodes'] = str(compgrp.servers())
        tbl.append(fields)


def setup_table(options, fmt=None):
    """
    Return a TextTable already setup based on display command line options like
    color and header.
    """
    tbl = TextTable(fmt)
    tbl.color = (options.color == 'auto' and Globals()['color'] == 'auto' \
                      and sys.stdout.isatty()) or \
                (options.color == 'auto' and Globals()['color'] == 'always') \
                or (options.color == 'always')

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
    viewsupports = None

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
        tbl.fmt = "%target %type %>index %node %primary %servers " \
                  "%device %status"
        tbl.header_labels = {'index': 'idx'}
        key = lambda t: (t.DISPLAY_ORDER, t.label)
        viewsupports = "index"

    elif view == "disk":
        tbl.title = "FILESYSTEM DISKS (%s)" % fs.fs_name
        tbl.fmt = "%device %servers %>size %>jdev %type %>index %tag %label " \
                  "%flags %fsname %status"
        tbl.header_labels = { 'size': 'dev_size', 'jdev': 'journal_device'}
        tbl.optional_cols = ['jdev', 'tag']
        key = lambda t: (t.DISPLAY_ORDER, t.label)
        viewsupports = "dev"

    table_fill(tbl, fs, sort_key=key, supports=supports,
               viewsupports=viewsupports)
    return str(tbl)
