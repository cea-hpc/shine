# Debug.py -- Impl. class for command debugging support 
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

from ClusterShell.Task import task_self

class Debug:
    
    def __init__(self, cmd):

        attr = { 'optional' : True,
                 'hidden' : True,
                 'doc' : "enable debugging" }

        self.cmd = cmd
        self.cmd.add_option('d', None, attr, cb=self.on_debug)

    def has_debug(self):
        return self.cmd.opt_d
    
    def on_debug(self, opt, arg):
        task = task_self()
        task.set_info("debug", True)

