# Format.py -- Format file system targets
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
from Base.RemoteCommand import RemoteCommand

from Shine.Lustre.FSLocal import FSLocal
from Shine.Lustre.FSProxy import FSProxy

from Base.RemoteCommand import RemoteCommand
from Base.Support.FS import FS
from Base.Support.Target import Target


# ----------------------------------------------------------------------
# * shine format
# ----------------------------------------------------------------------
class Format(RemoteCommand):
    
    def __init__(self):
        RemoteCommand.__init__(self)

        self.fs_support = FS(self) # XXX add : force one FS ?
        self.target_support = Target(self)

    def get_name(self):
        return "format"

    def get_desc(self):
        return "Format file system targets."

    def execute(self):
        if not self.opt_f:
            raise "No FS"
        else:
            assert self.local_flag
            target = self.target_support.get_target()
            for fsname in self.fs_support.iter_fsname():
                conf = Configuration(fs_name=fsname)
                fs = FSLocal(conf)
                fs.format(target)

