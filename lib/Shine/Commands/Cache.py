# Cache.py -- FS Cache ops
# Copyright (C) 2008 CEA
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

from Shine.Utilities.AsciiTable import AsciiTable, AsciiTableLayout

from Base.Command import Command

import sys


# ----------------------------------------------------------------------
# * shine cache (hidden command for debugging purposes)
# ----------------------------------------------------------------------
class Cache(Command):

    def __init__(self):
        Command.__init__(self)

    def is_hidden(self):
        return True

    def get_name(self):
        return "cache"

    def get_desc(self):
        return "FS/conf cache-related operations"

    def execute(self):
        if len(self.arguments) < 2:
            print "Usage: cache <info|show|del> <value> ..."
            sys.exit(1)
            
        cmd, val = self.arguments[0:2]
        if cmd == "show":
            conf = Configuration(fs_name=val)
            status_dic = conf.get_status_clients()

            ldic = []
            for node, val in status_dic.iteritems():
                dic = {}
                dic['node'] = node
                dic['status'] = val['status']
                d = val['date']
                dic['date'] = d.strftime("%Y-%m-%d %H:%M:%S")
                if val['options']:
                    dic['options'] = val['options']
                else:
                    dic['options'] = "None"
                ldic.append(dic)

            layout = AsciiTableLayout()

            layout.set_show_header(True)
            layout.set_column("node", 0, AsciiTableLayout.LEFT)
            layout.set_column("status", 1, AsciiTableLayout.LEFT)
            layout.set_column("date", 2, AsciiTableLayout.CENTER)
            layout.set_column("options", 3, AsciiTableLayout.LEFT)

            AsciiTable().print_from_list_of_dict(ldic, layout)

            
