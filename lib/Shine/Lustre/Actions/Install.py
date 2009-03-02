# Install.py -- Install Lustre FS configuration
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

from Action import Action, ActionFailedError

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker

import os
import sys

class Install(Action):
    """
    Action class: install file system configuration requirements on remote nodes.
    """

    def __init__(self, nodes, fs, fs_config_file):
        Action.__init__(self)
        self.nodes = nodes
        self.fs = fs
        self.fs_config_file = fs_config_file

    def launch(self):
        """
        Copy local configuration file to remote nodes.
        """
        self.task.copy(self.fs_config_file, self.fs_config_file,
                nodes=self.nodes, handler=self)

    def ev_start(self, worker):
        print "Updating file system configuration files on %s" % self.nodes

    def ev_close(self, worker):
        for rc, nodeset in worker.iter_retcodes():
            if rc != 0:
                raise ActionFailedError(rc, "Fatal: Installation of file system "
                    "configuration failed on %s (%s)" % (nodeset,
                    os.strerror(rc)))

