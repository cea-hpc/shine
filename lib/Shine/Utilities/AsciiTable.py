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


# Use an AsciiTable object when you want to print nice ascii-table from
# data. The following class accepts several input data formats.

import os
import sys


class AsciiTableLayout:
    """
    AsciiTable layout options class
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
        self._show_header = show_header

    def set_column(self, head_key, pos, align, title=None):
        self._pos[pos] = (head_key, title or head_key)
        if head_key not in self._layout:
            lay = { "align" : align }
            self._layout[head_key] = lay
        else:
            self._layout[head_key]['align'] = align

    # Getters
    #
    def show_header(self):
        return self._show_header

    def keys(self):
        lst = []
        for c in self:
            lst.append(c)
        return lst
            
    def __iter__(self):
        "Iterate over available columns."
        for i in range(len(self._pos)):
            yield self._pos[i]                  # FIXME always exists ?

    # Format
    #
    def format_string(self, head_key, length, str):
        align = self._layout[head_key]['align']
        if align == AsciiTableLayout.CENTER:
            return str.center(length)
        elif align == AsciiTableLayout.LEFT:
            return str.ljust(length)
        else:
            return str.rjust(length)


class AsciiTable:
    
    columns = 800

    def __init__(self, out=sys.stdout):
        self.out = out

# Usage for get_term_cols methods:
# termios: 0.00143790245056
# curses:  0.00277400016785

    def get_term_cols_from_curses(cls):
        import curses
        curses.setupterm()
        cls.columns = curses.tigetnum("cols")
        return cls.columns
    get_term_cols_from_curses = classmethod(get_term_cols_from_curses)

    def get_term_cols_from_environ(cls):
        cls.columns = int(os.environ['COLUMNS'])
        return cls.columns
    get_term_cols_from_environ = classmethod(get_term_cols_from_environ)

    def get_term_cols_from_termios(cls):
        global fcntl, struct, termios
        import fcntl, struct, termios
        s = struct.pack('HHHH', 0, 0, 0, 0)
        x = fcntl.ioctl(self.out.fileno(), termios.TIOCGWINSZ, s)
        cls.columns = struct.unpack('HHHH', x)[1]
        return cls.columns
    get_term_cols_from_termios = classmethod(get_term_cols_from_termios)

    def get_term_cols(cls):
        try:
            return cls.get_term_cols_from_termios()
        except:
            pass
        try:
            return cls.get_term_cols_from_curses()
        except:
            pass
        try:
            return cls.get_term_cols_from_environ()
        except:
            return cls.columns
    get_term_cols = classmethod(get_term_cols)


    def print_from_list_of_dict(self, rows, layout=None):
        """
        Generic method to print list of dictionaries with optional layout support.
        """

        # Get the number of columns for the current terminal (screen width)
        ncols = AsciiTable.get_term_cols()

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
                # if multilines, be carefull to fill the "virtual cells" with empty strings
                headers[t].append("")
                appended += 1

        # Calc max length for each column
        for row in rows:  
            for k, t in keys:
                val = row[k]
                sz = len(str(val))
                if max_col[k] < sz:
                    max_col[k] = sz

        # Handle multi lines
        key_lst = [[ keys[0] ]]
        block=0

        # The following code will adjust the max length for each column if necessary
        csize = max_col[keys[0][0]] + 3
        for k, t in keys[1:]:
            # Check if the table fits or not
            if csize + max_col[k] + 2 >= ncols and len(key_lst[block][1]) > 1:
                # Build other block table, with duplicated item 0
                key_lst.append([keys[0]])
                block += 1
                csize = max_col[keys[0][0]] + 3
            key_lst[block].append((k, t))
            max_col[k] = min(ncols - csize - 2, max_col[k])
            if max_col[k] <= 0:
                max_col[k] = 1
            csize += max_col[k] + 2

        #
        # Print headers
        #
        for tab in key_lst:
            sep_line = "+"
            for k, t in tab:
                sep_line += (max_col[k] + 1) * "-" + "+"

            self.out.write(sep_line + "\n")

            if layout.show_header():
                for l in range(0, lines):
                    self.out.write("|")
                    for k, t in tab:
                        self.out.write( "%-*s" % (max_col[k]+1, str(headers[t][l])) + "|" )
                    self.out.write("\n")
                self.out.write("%.*s\n" % (ncols, sep_line))

            #
            # Print data rows
            #
            for row in rows:
                s = "|"
                line_sup = s
                for k, t in tab:
                    target = row[k]
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
                        to_print = s + layout.format_string(k, max_col[k], splt[0]) + " |"
                        for w in splt[1:]:
                            to_print += line_sup + layout.format_string(k, max_col[k], w) + " |\n"
                        to_print = to_print[:-1]
                        break
                    else:
                        s += layout.format_string(k, max_col[k], target) + " |"
                        line_sup += (max_col[k] + 2) * " "
                        to_print = s
                    
                self.out.write(to_print + "\n")
            self.out.write(sep_line + "\n")


    def print_from_simple_dict(self, dictionary, head_key="Param", head_val="Value"):
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


