# AdditionalOptions.py -- Impl. class to deal with Additional options
# Copyright (C) 2010 BULL S.A.S
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

from Shine.Configuration.Globals import Globals 

class AdditionalOptions:
    """
    Additional options command parameter support
    """

    def __init__(self, cmd):
        attr = { 'optional' : True,
                 'hidden' : False,
                 'doc' : "additional options for final command" }

        self.cmd = cmd
        self.cmd.add_option('o', "Additional options", attr)

    def has_mount_options(self):
        return self.cmd.opt_o

    def get_options(self):
        """
        Function in charge of building the list of additional options 
        that must be used by the client nodes.
        """
        # Does the use provide some additional command line options
        if self.cmd.opt_o:
            return self.cmd.opt_o
        return None
