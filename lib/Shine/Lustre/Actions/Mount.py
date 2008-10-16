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

from Shine.Commands.CommandRegistry import CommandRegistry

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker
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
        self.mntp = None

    def launch(self):
        """
        Mount file system target.
        """
        if not self.target:
            # Client mounts
            self.mntp = self.fs.config.get_mount_path()
            assert self.mntp != None
            cmd = "mkdir -p \"%s\" && /bin/mount -t lustre %s:/%s \"%s\"" % (self.mntp,
                self.fs.get_mgs_nid(), self.fs.config.get_fs_name(), self.mntp)
        else:
            # Server mounts
            self.mntp = self.target.mntp
            cmd = "mkdir -p \"%s\" && /bin/mount -t lustre %s \"%s\"" % (self.mntp,
                    self.target.dev, self.mntp)
            #cmd = "mkdir -p \"%s\" && /bin/mount -t lustre -o abort_recov %s \"%s\"" % (self.mntp,
            #        self.target.dev, self.mntp)

        self.task.shell(cmd, handler=self)

    def ev_start(self, worker):
        if self.target:
            # server mounts
            CommandRegistry.output(msg="STARTING",
                                   target=self.target.target_name,
                                   dev=self.target.dev)
        else:
            # client mounts
            CommandRegistry.output(msg="MOUNTING",
                                   fs=self.fs.fs_name,
                                   mntp=self.mntp)

        sys.stdout.flush()

    def ev_close(self, worker):
        rc = worker.retcode()
        if self.target:
            CommandRegistry.output(msg="RESULT",
                                   target=self.target.target_name,
                                   dev=self.target.dev,
                                   rc=rc,
                                   buf=worker.read())
        else:
            CommandRegistry.output(msg="RESULT",
                                   fs=self.fs.fs_name,
                                   mntp=self.mntp,
                                   rc=rc,
                                   buf=worker.read())

