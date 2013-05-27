# Mount.py -- Lustre action class : mount
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

from Action import Action

from Shine.Utilities.Cluster.NodeSet import NodeSet
from Shine.Utilities.Cluster.Event import EventHandler
from Shine.Utilities.Cluster.Task import Task
from Shine.Utilities.Cluster.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable

import os
import sys

class Mount(Action):
    """
    File system format action class.
    """

    def __init__(self, task, fs, target=None):
        Action.__init__(self, task)
        self.fs = fs
        self.target = target

    def launch(self):
        """
        Mount file system target.
        """
        if self.target:
            # Server mounts
            mntp = self.target.mntp
            cmd = "mkdir -p \"%s\" && /bin/mount -t lustre %s \"%s\"" % (mntp, self.target.dev, mntp)
        else:
            mntp = self.fs.config.get_mount_path()
            assert mntp != None
            cmd = "mkdir -p \"%s\" && /bin/mount -t lustre %s:/%s \"%s\"" % (mntp,
                self.fs.get_mgs_nid(), self.fs.config.get_fs_name(), mntp)

        #cmd = "false"
        #cmd = "sleep 4"
        self.task.shell(cmd, handler=self)

    def ev_start(self, worker):
        if self.target:
            # server mounts
            print "Starting %s (%s)" % (self.target.target_name, self.target.dev)
        else:
            # client mounts
            print "Mounting %s" % self.fs.fs_name
        sys.stdout.flush()

    def ev_close(self, worker):
        rc = worker.get_rc()
        if self.target:
            if rc != 0:
                print "Starting of %s (%s) failed with error %d" % (self.target.target_name, self.target.dev, rc)
                print worker.read_buffer()
        else:
            if rc != 0:
                print "Mounting of %s failed: %s" % (self.fs.fs_name, os.strerror(rc))
                print worker.read_buffer()
                sys.exit(1)
            else:
                print "File system %s successfully mounted on %s" % (self.fs.fs_name, self.fs.config.get_mount_path())
        sys.stdout.flush()

