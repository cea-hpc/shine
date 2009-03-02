# Status.py -- Check remote target status
# Copyright (C) 2009 CEA
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

from Shine.FSUtils import open_lustrefs

from Base.RemoteCommand import RemoteCommand
from Base.Support.FS import FS
from Base.Support.Indexes import Indexes
from Base.Support.Nodes import Nodes
from Base.Support.Target import Target
from Base.Support.Quiet import Quiet
from RemoteCallEventHandler import RemoteCallEventHandler

#from Shine.Lustre.EventHandler import EventHandler
import Shine.Lustre.EventHandler

from ClusterShell.NodeSet import NodeSet

import os
import socket

class Status(RemoteCommand):
    """
    shine status -f <filesystem> -t <type> -i <index>
    """

    def __init__(self):
        RemoteCommand.__init__(self)

        self.fs_support = FS(self)
        self.indexes_support = Indexes(self)
        self.target_support = Target(self)


    def get_name(self):
        return "status"

    def get_desc(self):
        return "Check for file system target status."

    def execute(self):

        assert self.remote_call, "Not implemented yet"

        target = self.target_support.get_target()
        for fsname in self.fs_support.iter_fsname():

            if self.remote_call:
                handler = RemoteCallEventHandler()

            fs_conf, fs = open_lustrefs(fsname, target,
                    nodes=NodeSet(socket.gethostname()),
                    indexes=self.indexes_support.get_rangeset(),
                    event_handler=handler)

            fs.set_debug(self.debug_support.has_debug())

            fs.status()

