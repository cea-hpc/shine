# AsciiTable.py -- Print nice ascii-tables from data
# Copyright or (c) or Copr. 2007, CEA and Bull S.A.S.
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
AsciiTable module

Use an AsciiTable object when you want to print nice ascii-table from
data. The following class accepts several input data formats.
"""

import copy
import os
import sys


class AsciiTableLayout:
    """
    AsciiTable layout options class. This class is used to configure
    custom column layout for AsciiTable objects.
    """

    LEFT = 0
    RIGHT = 1
    CENTER = 2

    def __init__(self):
        self._layout = {}
        self._pos = {}
        self._show_header = True

    # Setters
    #
    def set_show_header(self, show_header):
        """If show_header is set to True, show title header row."""
        self._show_header = show_header

    def set_column(self, head_key, pos, align, title=None, title_align=None):
        """Configure a new column layout."""
        self._pos[pos] = (head_key, title or head_key)
        title_align = title_align or align
        if head_key not in self._layout:
            lay = { "align" : align, "title_align" : title_align }
            self._layout[head_key] = lay
        else:
            self._layout[head_key]['align'] = align
            self._layout[head_key]['title_align'] = title_align

    # Getters
    #
    def show_header(self):
        """Return True if the title header row is enabled."""
        return self._show_header

    def keys(self):
        """Get layout keys."""
        return list(self)
            
    def __iter__(self):
        "Iterate over available columns."
        for i in range(len(self._pos)):
            yield self._pos[i]                  # FIXME always exists ?

    # Format
    #
    def _format_string(self, align, length, in_str):
        if align == AsciiTableLayout.CENTER:
            return in_str.center(length)
        elif align == AsciiTableLayout.LEFT:
            return in_str.ljust(length)
        else:
            return in_str.rjust(length)

    def format_string(self, head_key, length, in_str):
        align = self._layout[head_key]['align']
        return self._format_string(align, length, in_str[:length])

    def format_title_string(self, head_key, length, in_str):
        align = self._layout[head_key]['title_align']
        return self._format_string(align, length, in_str[:length])

class AsciiTable:
    """
    Main class used to display ascii-based table.
    """
    
    columns = 800

    def __init__(self, out=sys.stdout):
        self.out = out

# Usage for get_term_cols methods:
# termios: 0.00143790245056
# curses:  0.00277400016785

    def get_term_cols_from_curses(self):
        import curses
        curses.setupterm()
        self.columns = curses.tigetnum("cols")
        return self.columns

    def get_term_cols_from_environ(self):
        self.columns = int(os.environ['COLUMNS'])
        return self.columns

    def get_term_cols_from_termios(self):
        global fcntl, struct, termios
        import fcntl, struct, termios
        s = struct.pack('HHHH', 0, 0, 0, 0)
        x = fcntl.ioctl(self.out.fileno(), termios.TIOCGWINSZ, s)
        self.columns = struct.unpack('HHHH', x)[1]
        return self.columns

    def get_term_cols(self):
        """Method to get the number of columns in a  terminal. Several
        methods are tried (termios, curses, environ)."""
        try:
            return self.get_term_cols_from_termios()
        except:
            pass
        try:
            return self.get_term_cols_from_curses()
        except:
            pass
        try:
            return self.get_term_cols_from_environ()
        except:
            return AsciiTable.columns

    def print_from_list_of_dict(self, rows, layout=None):
        """
        Generic method to print list of dictionaries with optional layout support.
        """

        # Get the number of columns for the current terminal (screen width)
        ncols = self.get_term_cols()

        # Get the column's keys in correct order according to defined layout
        keys = layout.keys()

        # Count the number of lines needed to display the column titles
        max_col = {}
        lines = 1
        for k, t in keys:
            max_col[k] = 0
            lines = max(t.count("\n") + 1, lines)

        # Build a list of lines for each title's cell
        headers = {}
        for k, t in keys:
            k_lst = t.split("\n")
            headers[t] = []
            appended = 0
            for line in k_lst:
                headers[t].append(line)
                max_col[k] = max(max_col[k], len(line))
                appended += 1
            while appended < lines:
                # if multilines, be carefull to fill the "virtual
                # cells" with empty strings
                headers[t].append("")
                appended += 1

        # Calc max length for each column
        for row in rows:  
            for k, t in keys:
                val = row[k]
                sz = len(str(val))
                if max_col[k] < sz:
                    max_col[k] = sz

        # The following code will adjust the max length for each column
        # if necessary
        csize = 0
        for k, t in keys:
            csize += max_col[k] + 2
        if csize > ncols:
            # table size do not fit screen, so we reduce size of columns
            # reference column size
            fixedsz = len(keys) * 2 + 1
            refcolsz = int((ncols - fixedsz) / len(keys))
            # redistribute chars not used by small columns
            gain, gaincnt = 0, 0
            for k, t in keys:
                if max_col[k] < refcolsz:
                    # remember chars gained in small cols
                    gain += refcolsz - max_col[k]
                    gaincnt += 1
            # recalc new reference column size for other columns
            refcolsz = refcolsz + gain/(len(keys) - gaincnt)
            for k, t in keys:
                if max_col[k] > refcolsz:
                    # this one is too big, reduce col size to
                    # reference size
                    max_col[k] = refcolsz
            # last adjustment to fit exactly to screen
            total = fixedsz
            for k, t in keys:
                total += max_col[k]
            # increase largest column(s) by 1
            for k, t in sorted(keys, cmp=lambda x, y: cmp(max_col[y[0]],
                                                          max_col[x[0]])):
                if total < ncols - 1:
                    max_col[k] += 1
                    total += 1

        tab = keys

        #
        # Print headers
        #
        sep_line = "+"
        for k, t in tab:
            sep_line += (max_col[k] + 1) * "-" + "+"
        self.out.write(sep_line + "\n")

        if layout.show_header():
            for l in range(0, lines):
                self.out.write("|")
                for k, t in tab:
                    self.out.write( layout.format_title_string(k,
                        max_col[k], str(headers[t][l])) + " |" )
                self.out.write("\n")
            self.out.write("%.*s\n" % (ncols, sep_line))

        spltbuf_ref = dict.fromkeys([it[0] for it in keys])
        for k in spltbuf_ref:
            spltbuf_ref[k] = []

        #
        # Print data rows
        #
        for row in rows:
            spltbuf = copy.deepcopy(spltbuf_ref)
            to_print = "|"
            for k, t in tab:
                target = str(row[k])
                offset = 0
                splt = []
                while offset + max_col[k] < len(target):
                    w = target[offset:offset+max_col[k]]
                    offset += max_col[k]
                    splt.append(w)
                else:
                    w = target[offset:]
                    splt.append(w)

                if len(splt) > 1:
                    to_print += layout.format_string(k, max_col[k], splt[0]) \
                                    + " |"
                    for i in range(1, len(splt)):
                        spltbuf[k].append(splt[i])
                else:
                    to_print += layout.format_string(k, max_col[k], target) \
                                    + " |"
                
            self.out.write(to_print + "\n")

            # multi-line support: print additional lines
            max_lb = 0
            for k, lb in spltbuf.iteritems():
                max_lb = max(max_lb, len(lb))

            for ik in range(0, max_lb):
                for k, t in tab:
                    if ik < len(spltbuf[k]):
                        self.out.write("|+" + layout.format_string(k,
                                                max_col[k], spltbuf[k][ik]))
                    else:
                        self.out.write("|" + layout.format_string(k,
                                                max_col[k] + 1, ''))
                self.out.write("|\n")

        self.out.write(sep_line + "\n")


    def print_from_simple_dict(self, dictionary, head_key="Param",
                               head_val="Value"):
        """
        Print from a simple dictionary data (key, simple value).
        Example: ascii_table.print_from_simple_dict(dict, "Param", "Value")
        """

        lst = []

        # We like it sorted.
        sorted_keys = dictionary.keys()
        sorted_keys.sort()

        # Create the list of dict entries we need, for each item of the list,
        # create a dictionary with key=(column header name). If no header is
        # specified, we use dummy keys 0 and 1.
        for k in sorted_keys:
            lst.append(dict([(head_key, k), (head_val, dictionary[k])]))

        # Create simple dict layout
        layout = AsciiTableLayout()

        layout.set_show_header(True)

        layout.set_column(head_key, 0, AsciiTableLayout.LEFT)
        layout.set_column(head_val, 1, AsciiTableLayout.LEFT)

        # Will do the job...
        self.print_from_list_of_dict(lst, layout)


