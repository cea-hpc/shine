# Umount.py -- Lustre proxy action class : umount
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

from Shine.Utilities.Cluster.NodeSet import NodeSet
from Shine.Utilities.Cluster.Event import EventHandler
from Shine.Utilities.Cluster.Task import Task
from Shine.Utilities.Cluster.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable

import os
import sys

class Umount(ProxyAction):
    """
    File system umount proxy action class.
    """

    def __init__(self, task, fs, nodes):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.nodes = nodes

    def launch(self):
        """
        Proxy file system umount command.
        """
        # Prepare proxy command
        command = "%s umount -f %s -L" % (self.progpath, self.fs.fs_name)

        # Run cluster command
        self.task.shell(command, nodes=self.nodes, handler=self)
        self.task.run()

    def ev_read(self, worker):
        print "%s: %s" % worker.get_last_read()

    def ev_close(self, worker):
        gdict = worker.gather_rc()
        for nodes, rc in gdict.iteritems():
            if rc != 0:
                self.fs.config.set_status_clients_umount_failed(nodes, None)
                raise ActionFailedError(rc, "Unmounting client failed on %s" % nodes.as_ranges())
            else:
                self.fs.config.set_status_clients_umount_complete(nodes, None)
                print "File system %s successfully unmounted on %s" % (self.fs.fs_name,
                    nodes.as_ranges())
    
