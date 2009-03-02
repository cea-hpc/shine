# FSProxy.py -- Lustre FileSystem Proxy Actions Class
# Copyright (C) 2007, 2008, 2009 CEA
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

from EventHandler import *
from FileSystem import *
from Target import *



class FSProxy(FileSystem):
    """
    Lustre.FileSystem proxy class. Redirect actions for remote execution.
    """

    def __init__(self, fs_name):
        FileSystem.__init__(fs_name)

    def start(self):
        """
        Start file system globally.
        """

        self.invoke('evt_target', EV_START, self.targets[0])

        last_target = None
        for target in self.targets:
            if last_target and target > last_target:
                pass

    def stop(self, target):
        pass

    def status(self, target, view):
        pass

    def info(self):
        pass

