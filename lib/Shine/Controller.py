# Controller.py -- Controller class
# Copyright (C) 2007 CEA
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

from Configuration.Globals import Globals
from Commands.CommandRegistry import CommandRegistry

from Configuration.ModelFile import ModelFileException

import getopt

class Controller:

    def __init__(self):
        self.cmds = CommandRegistry()

    def cmds_usage(self):
        cmd_maxlen = 0
        for cmd in self.cmds:
            if len(cmd.get_name()) > cmd_maxlen:
                cmd_maxlen = len(cmd.get_name())
        for cmd in self.cmds:
            print "\t%-*s %s" % (cmd_maxlen, cmd.get_name(), cmd.get_params_desc())

    def run_command(self, cmd_name, args):
        try:
            self.cmds.execute(cmd_name, args)
        except getopt.GetoptError, e:
            print "Syntax error: %s %s" % (cmd_name, e)
        except ModelFileException, e:
            print "ModelFile: %s" % e
        except KeyError:
            print "Error - Unrecognized action: %s" % cmd_name
            print
            raise


