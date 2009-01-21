# InstallTuningConf.py -- Install Lustre FS tuning configuration parameter
# Copyright (C) 2007 BULL/CEA
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
# $Id: Install.py 28 2008-04-25 23:48:50Z st-cea $

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.TuningModel import TuningModel

from Action import Action, ActionFailedError

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker

import os
import sys

class InstallTuningConf(Action):
    """
    Action class: install file system tuning configuration requirements on remote nodes.
    """

    def __init__(self, task, fs, clients=None, 
                 tuning_filename=Globals().get_tuning_file()):
        Action.__init__(self, task)
        self.fs = fs
        if clients:
            # Install on clients
            self.nodes = NodeSet(clients)
        else:
            # Install on I/O nodes
            self.nodes = self.fs.get_target_nodes()
            
        self.tuning_filename = tuning_filename

    def launch(self):
        """
        Do it.
        """
        dst = src = self.tuning_filename
        self.task.copy(dst, src, nodes=self.nodes, handler=self)

    def ev_start(self, worker):
        print "Updating file system tuning configuration files on %s" % \
                self.nodes

    def ev_close(self, worker):
        for rc, nodelist in worker.iter_retcodes():
            if rc != 0:
                raise ActionFailedError(rc, \
                        "Fatal: Installation of file system tuning configuration failed on %s (%s)" \
                        % (NodeSet.fromlist(nodelist), os.strerror(rc)))

