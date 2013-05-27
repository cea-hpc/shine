# Install.py -- File system installation commands
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
from Shine.Commands.Base.Command import Command

from Shine.Lustre.FSProxy import FSProxy

import getopt

# ----------------------------------------------------------------------
# * shine install
# ----------------------------------------------------------------------
class Install(Command):
    def get_name(self):
        return "install"

    def get_params_desc(self):
        return "-f <LMF path>"

    def get_desc(self):
        return "Install a new file system."

    def execute(self, args):
        try:
            lmf_path = None
            options, arguments = getopt.getopt(args, "f:")
            for opt, arg in options:
                if opt == '-f':
                    lmf_path = arg
            if lmf_path:
                conf = Configuration(lmf=arg)
                fs = FSProxy(conf)
                fs.install()
                fs.format()
                print "File system %s is now installed and ready to use." % conf.get_fs_name()
                print "Use `shine start -f %s' to start it." % conf.get_fs_name()

            else:
                # XXX raise something
                print "Bad argument"

        except getopt.GetoptError:
            raise
        except ConfigException, e:
            print e
        except IOError, e:
            print e

