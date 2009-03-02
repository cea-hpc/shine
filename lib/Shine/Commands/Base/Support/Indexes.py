# Indexes.py -- Impl. class for command indexes support 
# Copyright (C) 2009 CEA
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


from ClusterShell.NodeSet import RangeSet


class Indexes:
    """
    Command support class for "-i <index_rangeset>" command option.
    """
    def __init__(self, cmd):

        attr = { 'optional' : True,
                 'hidden' : False,
                 'doc' : "specify target index ranges, eg. 0-6/2" }

        self.cmd = cmd
        self.cmd.add_option('i', 'index(es)', attr)

    def get_rangeset(self):
        if self.cmd.opt_i:
            return RangeSet(self.cmd.opt_i)
        return None

