# Show.py -- Show shine configs
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
# * shine show
# ----------------------------------------------------------------------
class Show(Command):

    def __init__(self):
        Command.__init__(self)

    def is_hidden(self):
        return False

    def get_name(self):
        return "show"

    def get_desc(self):
        return "Show conf and misc internals"

    def execute(self):
        if len(self.arguments) < 1:
            print "Usage: show <conf|storage>"
            sys.exit(1)
            
        cmd = self.arguments[0]
        if cmd == "conf":
            AsciiTable().print_from_simple_dict(Globals().get_dict())
        elif cmd == "storage":
            from Shine.Configuration.Backend.BackendRegistry import BackendRegistry
            from Shine.Configuration.Backend.Backend import Backend

            backend = BackendRegistry().get_selected()
            backend.start() 

            devs = backend.get_target_devices('mgt')
            for dev in devs:
                print dev

            devs = backend.get_target_devices('mdt')
            for dev in devs:
                print dev

            devs = backend.get_target_devices('ost')
            for dev in devs:
                print dev


            
