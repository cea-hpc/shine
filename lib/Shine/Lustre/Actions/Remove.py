# Install.py -- Install Lustre FS configuration
# Copyright (C) 2007 BULL S.A.S
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
 
# Import Section
from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

from Shine.Commands.CommandRegistry import CommandRegistry
from Action import Action, ActionFailedError

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker

import os
import sys
import socket
import binascii
import pickle

class Remove(Action):
    """
    Action class: Remote file system configuration requirements on remote
    nodes.
    """

    def __init__(self, task, fs):
        Action.__init__(self, task)
        self.fs = fs

    def launch(self):
        """
        Do it.
        """
        # Build the command which must be executed on this node
        # to remove de file system.
        cmd = "/bin/rm -f %s" % self.fs.config.get_cfg_filename()

        # Start the command on the local node
        self.task.shell(cmd, handler=self)

    def ev_start(self, worker):
        # send a message for the start of the remove process
        CommandRegistry.output(msg="REMOVING")

        sys.stdout.flush()

    def ev_close(self, worker):
        rc = worker.retcode()

        # Send a message with the result of the removing command
        CommandRegistry.output(msg="RESULT",
                                rc=rc,
                                buf=worker.read())
