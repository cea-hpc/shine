# Mount.py -- Lustre proxy action class : mount
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

class Mount(ProxyAction):
    """
    File system mount proxy action class.
    """

    def __init__(self, task, fs, nodes):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.nodes = nodes
        self.record_buf = ""

    def launch(self):
        """
        Proxy file system mount command.
        """
        # Prepare proxy command for each different client mount path
        mounts = self.fs.config.get_client_mounts()

        for path, nodes in mounts.iteritems():

            # Build shine remote mount command
            command = "%s mount -f %s -R -M %s" % (self.progpath, self.fs.fs_name,
                path)

            print command

            # Schedule command for execution
            self.task.shell(command, nodes=nodes, handler=self)

        # Run cluster commands
        self.task.run()

    def ev_start(self, worker):
        print "Mounting %s: " % self.fs.fs_name,
        sys.stdout.flush()

    def ev_read(self, worker):
        node, msg = worker.get_last_read()
        if msg.find("successfully mounted on") >= 0:
            sys.stdout.write(".")
            sys.stdout.flush()
        elif msg.find("Mounting %s" % self.fs.fs_name) == -1:
            self.record_buf += "%s: %s\n" % (node, msg)

    def ev_close(self, worker):
        print
        fail_nodes = NodeSet()
        max_rc = 0

        gdict = worker.gather_rc()
        for nodes, rc in gdict.iteritems():
            if rc != 0:
                max_rc = max(max_rc, rc)
                fail_nodes.add(nodes)
            else:
                # TODO add mount options
                self.fs.config.set_status_clients_mount_complete(nodes, None)
                print "File system %s successfully mounted on %s" % (self.fs.fs_name,
                    nodes.as_ranges())
    
        if len(fail_nodes):
            self.fs.config.set_status_clients_mount_failed(fail_nodes, None)
            print self.record_buf
            raise ActionFailedError(max_rc,
                "Failed to mount client on %s" % fail_nodes.as_ranges())

