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
import datetime
import traceback


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

        #self.logger.info("running %s" % cmd_name)

        try:
            return self.cmds.execute(cmd_args)
        except getopt.GetoptError, e:
            print "Syntax error: %s" % e
        except CommandHelpException, e:
            self.print_help(e.message, e.cmd)
        except CommandException, e:
            self.print_error(e.message)
        except ModelFileIOError, e:
            print "Error - %s" % e.message
        except ModelFileException, e:
            print "ModelFile: %s" % e
        except ConfigException, e:
            print "Configuration: %s" % e
        # file system
        except FSRemoteError, e:
            self.print_error(e)
            return e.rc
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


