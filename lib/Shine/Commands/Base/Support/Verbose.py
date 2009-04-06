# Verbose.py -- Impl. class for command verb support 
# Copyright (C) 2008, 2009 CEA
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


class Verbose:
    
    def __init__(self, cmd, with_quiet=True):

        attr = { 'optional' : True,
                 'hidden' : False,
                 'doc' : "enable verbose output" }

        self.cmd = cmd
        self.cmd.add_option('v', None, attr)

        attr = { 'optional' : True,
                 'hidden' : not with_quiet,
                 'doc' : "enable quiet output" }

        self.cmd.add_option('q', None, attr)
    
    def has_verbose(self):
        return self.cmd.opt_v

    def has_quiet(self):
        return self.cmd.opt_q
    
    def get_verbose_level(self):
        """
        Get verbose level:
            0 = quiet, no output
            1 = standard
            2 = verbose ouptut
        """
        if self.has_quiet():
            return 0
        elif not self.has_verbose():
            return 1
        else:
            return 2

