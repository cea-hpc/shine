# FSClientCommand.py -- Base file system related command
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *
from Command import Command

from Shine.Lustre.FSLocal import FSLocal
from Shine.Lustre.FSProxy import FSProxy

import getopt
import sys

class FSClientCommand(Command):

    def get_params_desc(self):
        return "-f <fsname> -n <nodes>"

    def execute(self, args):
        try:
            fs_name = None
            fs_class = FSProxy
            nodes = None

            options, arguments = getopt.getopt(args, "f:Ln:")

            for opt, arg in options:
                if opt == '-f':
                    fs_name = arg
                elif opt == '-L':
                    fs_class = FSLocal
                elif opt == '-n':
                    nodes = arg
            if not fs_name:
                print "Error: at this time, you must specify -f <fsname>"
                sys.exit(1)

            try:
                conf = Configuration(fs_name=fs_name)

                if fs_class == FSLocal:
                    self.fs_execute(fs_class(conf))
                elif not nodes:
                    # FIXME because
                    print "Error: use -n to specify nodes ranges"
                    sys.exit(1)
                else:
                    self.fs_execute(fs_class(conf), nodes)
            finally:
                conf.close()

        except getopt.GetoptError, e:
            print e
            sys.exit(1)
        except ConfigException, e:
            print e
            sys.exit(1)
        except IOError, e:
            print e
            sys.exit(1)

    def fs_execute(self, fs, **kwargs):
        raise NotImplementedError("Derived classes must implement.")

