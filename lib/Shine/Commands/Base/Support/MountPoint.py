# MountPoint.py -- Impl. class for -M mntpt option
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

from Shine.Lustre.FSLocal import FSLocal
from Shine.Lustre.FSProxy import FSProxy

from ClusterShell.NodeSet import NodeSet

class MountPoint:
    
    def __init__(self, cmd, optional=True):

        attr = { 'optional' : optional,
                 'hidden' : False,
                 'doc' : "mount point (a valid path)" }

        self.cmd = cmd
        self.cmd.add_option('M', 'mntpt', attr)

    
    def get_mntpt(self):
        if self.cmd.opt_M:
            return self.cmd.opt_M
        return None


