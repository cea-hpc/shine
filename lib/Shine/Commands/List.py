# List.py -- List installed filename names.
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
Shine `list' command classes.

List installed filename names.
"""

from Shine.Commands.Base.Command import Command

class List(Command):
    """
    shine list
    """

    NAME = "list"
    DESCRIPTION = "List installed filename names."

    def execute(self):

        # Option sanity check
        self.forbidden(self.options.fsnames, "-m, see -f")
        self.forbidden(self.options.labels, "-f")
        self.forbidden(self.options.labels, "-l")
        self.forbidden(self.options.indexes, "-i")
        self.forbidden(self.options.failover, "-F")

        print "\n".join(self.iter_fsname())
