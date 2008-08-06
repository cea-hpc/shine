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

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker
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
        self.good_nodes = NodeSet()
        self.fail_nodes = NodeSet()
        self.already_nodes = NodeSet()
        self.max_rc = 0

    def launch(self):
        """
        Proxy file system mount command.
        """
        # Prepare proxy command for each different client mount path
        mounts = self.fs.config.get_client_mounts(self.nodes)
        if len(mounts) == 0:
            print "Nothing to mount."
            return

        for path, nodes in mounts.iteritems():

            # Build shine remote mount command
            command = "%s mount -f %s -R -M %s" % (self.progpath, self.fs.fs_name,
                path)

            # Schedule command for execution
            self.task.shell(command, nodes=nodes, handler=self)

        # Run cluster commands
        self.task.run()

    def ev_start(self, worker):
        print "Mounting %s: " % self.fs.fs_name,
        sys.stdout.flush()

    def ev_read(self, worker):
        node, info = worker.get_last_read()
        dic = self._read_shine_msg(info)

        msg = dic['msg']

        dic['status'] = 'UNKNOWN'

        if msg == "MOUNTING":
            pass
        elif msg == "RESULT":
            rc = dic['rc']
            if rc == 0:
                self.good_nodes.add(node)
                sys.stdout.write(".")
                sys.stdout.flush()
            else:
                if rc > self.max_rc:
                    self.max_rc = rc
                msg = dic['buf']
                if msg.find("already mounted") >= 0:
                    self.already_nodes.add(node)
                    sys.stdout.write(".")
                    sys.stdout.flush()
                else:
                    self.fail_nodes.add(node)
                    lines = msg.splitlines(False)
                    if len(lines) > 0:
                        print
                    for line in lines:
                        print "%s: %s" % (node, line)

    def ev_close(self, worker):
        print
        if len(self.good_nodes) > 0:
            # TODO add mount options
            ###self.fs.config.set_status_clients_mount_complete(self.good_nodes, None)
            print "File system %s successfully mounted on %s" % (self.fs.fs_name,
                    self.good_nodes.as_ranges())
        if len(self.already_nodes) > 0:
            print "File system %s already mounted on %s" % (self.fs.fs_name,
                    self.already_nodes.as_ranges())
        if len(self.fail_nodes) > 0:
            ###self.fs.config.set_status_clients_mount_failed(self.fail_nodes, None)
            raise ActionFailedError(self.max_rc,
                "Failed to mount client on %s" % self.fail_nodes.as_ranges())

    def has_debug(self):
        return self.fs.debug
