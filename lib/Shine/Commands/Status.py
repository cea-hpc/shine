# Status.py -- Status of file system
# Copyright (C) 2007,2008 CEA
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *
from Base.MultiFSCommand import MultiFSCommand

from Shine.Utilities.AsciiTable import AsciiTable, AsciiTableLayout

import binascii, pickle

# ----------------------------------------------------------------------
# * shine status
# ----------------------------------------------------------------------
class Status(MultiFSCommand):

    def get_name(self):
        return "status"

    def get_params_desc(self):
        return "[-f <fsname>] [-t <target>]"

    def get_desc(self):
        return "Status of file system servers."

    def fs_execute(self, fs, fs_target):
        fs.status(fs_target)

    def output(self, dic):
        if self.remote_call:
            self._print_pickle(dic)
        else:
            ldic = dic['listofdic']

            # add fs name in table
            for d in ldic:
                d['fs'] = dic['fs']

            # Print nice table layout
            layout = AsciiTableLayout()

            layout.set_show_header(True)
            layout.set_column("fs", 0, AsciiTableLayout.LEFT)
            layout.set_column("node", 1, AsciiTableLayout.LEFT)
            layout.set_column("type", 2, AsciiTableLayout.CENTER)
            layout.set_column("name", 3, AsciiTableLayout.LEFT)
            layout.set_column("dev", 4, AsciiTableLayout.LEFT)
            layout.set_column("status", 5, AsciiTableLayout.CENTER)

            AsciiTable().print_from_list_of_dict(ldic, layout)


    
