# Install.py -- File system installation commands
# Copyright (C) 2007, 2008 CEA
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

from Shine.Lustre.FSProxy import FSProxy

from Base.Command import Command
from Base.Support.LMF import LMF

import getopt

# ----------------------------------------------------------------------
# * shine install
# ----------------------------------------------------------------------
class Install(Command):
    
    def __init__(self):
        Command.__init__(self)

        self.lmf_support = LMF(self)

    def get_name(self):
        return "install"

    def get_desc(self):
        return "Install a new file system."

    def execute(self):
        if not self.opt_f:
            print "Bad argument"
        else:
            conf = Configuration(lmf=self.opt_f)
            fs = FSProxy(conf)
            fs.install()
            ###
            fs.format()
            ###
            print "File system %s is now installed and ready to use." % conf.get_fs_name()
            print "Use `shine start -f %s' to start it." % conf.get_fs_name()

