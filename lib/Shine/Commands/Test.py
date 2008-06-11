# Test.py -- Test
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
from Shine.Lustre.FileSystem import FileSystem

from Base.Command import Command
from Base.Support.FS import FS

from Exceptions import *

from errno import *

import getopt
import os
import sys

import fcntl

# ----------------------------------------------------------------------
# * shine test
# ----------------------------------------------------------------------
class Test(Command):
    """
    Test command.
    """
    
    def __init__(self):
        Command.__init__(self)

        #self.fs_support = FS(self, optional=False)

    def get_name(self):
        return "test"

    def get_desc(self):
        return "General file system information."

    def execute(self):
        try:
          pass
        except IOError, e:
            raise


