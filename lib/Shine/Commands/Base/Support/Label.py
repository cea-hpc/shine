# Label.py -- Impl. class for command label support 
# Copyright (C) 2010 CEA
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

from ClusterShell.NodeSet import NodeSet

class Label(object):
    """
    Command support class for "-l <component label>" command option.
    """

    def __init__(self, cmd):
        self.cmd = cmd

        attr = { 'optional' : True,
                 'hidden' : False,
                 'doc' : "specify component by label (ie: lustre-OST0000)" }
        self.cmd.add_option('l', 'label', attr)

    def get_labels(self):
        if self.cmd.opt_l:
            return NodeSet(self.cmd.opt_l)
        return None
