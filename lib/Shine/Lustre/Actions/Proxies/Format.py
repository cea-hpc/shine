# Format.py -- Lustre proxy action class : format
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

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

from Shine.Lustre.Actions.Action import ActionFailedError
from ProxyAction import ProxyAction

from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.MGS import MGS
from Shine.Lustre.MDS import MDS
from Shine.Lustre.OSS import OSS

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable

import os
import sys

class Format(ProxyAction):
    """
    File system format action class.
    """

    def __init__(self, task, fs, target_name):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.target_name = target_name

    def launch(self):
        """
        Proxy file system format command.
        """

        # Prepare proxy command
        if not self.target_name:
            command = "%s format -f %s -L" % (self.progpath, self.fs.fs_name)
        else:
            command = "%s format -f %s -L -t %s" % (self.progpath, self.fs.fs_name, self.target_name)

        selected_nodes = self.fs.get_target_nodes(self.target_name)

        # Run cluster command
        self.task.shell(command, nodes=selected_nodes, handler=self)
        self.task.resume()

    def ev_read(self, worker):
        print "%s: %s" % worker.last_read()

    def ev_close(self, worker):
        gdict = worker.gather_rc()
        for nodelist, rc in gdict.iteritems():
            if rc != 0:
                raise ActionFailedError(rc, "Formatting failed on %s" % nodelist.as_ranges())

