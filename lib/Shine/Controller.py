# Controller.py -- Controller class
# Copyright (C) 2007-2011 CEA
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
from Shine.Configuration.ModelFile import ModelFileValueError
from Shine.Configuration.Exceptions import ConfigException

from Shine.Commands.CommandRegistry import CommandRegistry
from Shine.Commands.Exceptions import CommandHelpException, CommandException
from Shine.Commands.Base.CommandRCDefs import RC_RUNTIME_ERROR

from Shine.Lustre.FileSystem import FSRemoteError
from Shine.Lustre.Component import ComponentError

from ClusterShell.Task import task_self
from ClusterShell.NodeSet import NodeSetParseError, RangeSetParseError

import getopt
import re
import sys
import datetime
import traceback


def print_csdebug(task, s):
    m = re.search("(\w+): SHINE:\d:", s)
    if m:
        print "%s<pickle>" % m.group(0)
    else:
        print s


class Controller:

    def __init__(self):
        self.cmds = CommandRegistry()

        task = task_self()

        #task.set_info("debug", True)
        task.set_info("print_debug", print_csdebug)
        fanout = Globals().get_ssh_fanout()
        if fanout > 0:
            task.set_info("fanout", fanout)

    def usage(self):
        cmd_maxlen = 0

        for cmd in self.cmds:
            if not cmd.is_hidden():
                if len(cmd.NAME) > cmd_maxlen:
                    cmd_maxlen = len(cmd.NAME)
        for cmd in self.cmds:
            if not cmd.is_hidden():
                print "  %-*s %s" % (cmd_maxlen, cmd.NAME,
                    cmd.get_params_desc())

    def print_error(self, errmsg):
        print >> sys.stderr, "Error:", errmsg

    def print_help(self, msg, cmd):
        if msg:
            print msg
            print
        print "Usage: %s %s" % (cmd.NAME, cmd.get_params_desc())
        print
        print cmd.DESCRIPTION

    def save_exception(self, error, cmd_args):
        """
        Save the provided exception with its traceback in a file
        for latter analysis or bug report.
        """
        now = datetime.datetime.today().replace(microsecond=0)

        filename = '/tmp/shine-error-%s' % (now.isoformat('_'))
        f = open(filename, 'w')
        f.write("#\n# Shine error report - %s\n#\n\n" % now)
        f.write("Command was: 'shine %s'\n\n" % " ".join(cmd_args))
        traceback.print_exc(file=f)
        f.write("\n")
        f.write("Exception: %s\n\n" % error)
        f.close()

        return filename

    def run_command(self, cmd_args):

        try:
            return self.cmds.execute(cmd_args)
        except getopt.GetoptError, e:
            print "Syntax error: %s" % e
        except CommandHelpException, error:
            self.print_help(str(error), error.cmd)
        except CommandException, error:
            self.print_error(str(error))
        except ConfigException, e:
            print "Configuration: %s" % e
        except ModelFileValueError, error:
            self.print_error(str(error))
        # file system
        except FSRemoteError, e:
            self.print_error(e)
            return e.rc
        except ComponentError, e:
            self.print_error("%s" % e)
        except NodeSetParseError, e:
            self.print_error("%s" % e)
        except RangeSetParseError, e:
            self.print_error("%s" % e)

        #
        # Global catchall for all other errors
        # except KeyboardInterrupt and SystemExit
        #
        except (KeyboardInterrupt, SystemExit), e:
            raise e
        except Exception, e:
            print "Unknown error: %s" % e
            f = self.save_exception(e, cmd_args)
            print "(details in %s)" % f
        
        return RC_RUNTIME_ERROR


