# MultiFSCommand.py -- Base file system related command
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
from Command import Command

from Shine.Lustre.FSLocal import FSLocal
from Shine.Lustre.FSProxy import FSProxy

import getopt
import os
import sys

class MultiFSCommand(Command):
    
    def __init__(self):
        self.remote_call = False
        self.selected_fs = []

    def get_params_desc(self):
        return "[-f <fsname>]"

    def execute(self, args):
        try:
            fs_name = None
            fs_class = FSProxy
            fs_target = None

            options, arguments = getopt.getopt(args, "f:LRt:")

            for opt, arg in options:
                if opt == '-f':
                    fs_name = arg
                elif opt == '-L':
                    fs_class = FSLocal
                elif opt == '-R':
                    self.remote_call = True
                    fs_class = FSLocal
                elif opt == '-t':
                    fs_target = arg.lower()

            if not fs_name:
                for filename in os.listdir(Globals().get_conf_dir()):
                    name, ext = os.path.splitext(filename)
                    if len(name) > 0 and ext == '.xmf':
                        # XXX check for bogus xmf ?
                        self.selected_fs.append(name)
            else:
                self.selected_fs = [name.strip() for name in fs_name.split(',')]

            for selected_fs_name in self.selected_fs:
                conf = Configuration(fs_name=selected_fs_name)
                try:
                    self.fs_execute(fs_class(conf), fs_target)
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

    def fs_execute(self, fs):
        raise NotImplementedError("Derived classes must implement.")

