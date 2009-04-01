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
from Configuration.ModelFile import ModelFileIOError

from Configuration.Exceptions import ConfigException
from Commands.Exceptions import *
from Commands.Base.CommandRCDefs import *

from Lustre.FileSystem import FSRemoteError

from ClusterShell.Task import *
from ClusterShell.NodeSet import *

import getopt
import logging
import re
import sys


def print_csdebug(task, s):
    m = re.search("(\w+): SHINE:\d:(\w+):", s)
    if m:
        print "%s<pickle>" % m.group(0)
    else:
        print s


class Controller:

    def __init__(self):
        self.logger = logging.getLogger("shine")
        #handler = logging.FileHandler(Globals().get_log_file())
        #formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s : %(message)s')
        #handler.setFormatter(formatter)
        #self.logger.addHandler(handler)
        #self.logger.setLevel(Globals().get_log_level())
        self.cmds = CommandRegistry()

        #task_self().set_info("debug", True)

        task_self().set_info("print_debug", print_csdebug)

    def usage(self):
        cmd_maxlen = 0

        for cmd in self.cmds:
            if not cmd.is_hidden():
                if len(cmd.get_name()) > cmd_maxlen:
                    cmd_maxlen = len(cmd.get_name())
        for cmd in self.cmds:
            if not cmd.is_hidden():
                print "  %-*s %s" % (cmd_maxlen, cmd.get_name(),
                    cmd.get_params_desc())

    def print_error(self, errmsg):
        print >>sys.stderr, "Error:", errmsg

    def print_help(self, msg, cmd):
        if msg:
            print msg
            print
        print "Usage: %s %s" % (cmd.get_name(), cmd.get_params_desc())
        print
        print cmd.get_desc()

    def run_command(self, cmd_args):

        #self.logger.info("running %s" % cmd_name)

        try:
            return self.cmds.execute(cmd_args)
        except getopt.GetoptError, e:
            print "Syntax error: %s" % e
        except CommandHelpException, e:
            self.print_help(e.message, e.cmd)
        except CommandException, e:
            self.print_error(e.message)
            return RC_USER_ERROR
        except ModelFileIOError, e:
            print "Error - %s" % e.message
        except ModelFileException, e:
            print "ModelFile: %s" % e
        except ConfigException, e:
            print "Configuration: %s" % e
            return RC_RUNTIME_ERROR
        # file system
        except FSRemoteError, e:
            self.print_error(e)
            return e.rc
        except NodeSetParseError, e:
            self.print_error("%s" % e)
            return RC_USER_ERROR
        except RangeSetParseError, e:
            self.print_error("%s" % e)
            return RC_USER_ERROR
        except KeyError:
            print "Error - Unrecognized action"
            print
            raise
        
        return 1


