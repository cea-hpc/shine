# Umount.py -- Lustre action class : umount
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

class Umount(Action):
    """
    File system umount action class.
    """

    def __init__(self, task, fs, target=None):
        Action.__init__(self, task)
        self.fs = fs
        self.target = target

    def launch(self):
        """
        UnMount file system target.
        """
        if self.target:
            # Server umounts
            cmd = "/bin/umount \"%s\"" % self.target.mntp
        else:
            mntp = self.fs.config.get_mount_path()
            assert mntp != None
            cmd = "/bin/umount \"%s\"" % mntp

        self.task.shell(cmd, handler=self)

    def ev_start(self, worker):
        if self.target:
            # server umounts
            CommandRegistry.output(msg="STOPPING",
                                   target=self.target.target_name,
                                   dev=self.target.dev)
        else:
            # client umounts
            CommandRegistry.output(msg="UMOUNTING",
                                   fs=self.fs.fs_name)
        sys.stdout.flush()

    def ev_close(self, worker):
        rc = worker.get_rc()
        if self.target:

            CommandRegistry.output(msg="RESULT",
                                   target=self.target.target_name,
                                   dev=self.target.dev,
                                   rc=rc,
                                   buf=worker.read_buffer())
        else:
            if rc != 0:
                print "Unmounting of %s failed: %s" % (self.fs.fs_name, os.strerror(rc))
                print worker.read_buffer()
                sys.exit(1)
            else:
                print "File system %s successfully unmounted" % self.fs.fs_name
        sys.stdout.flush()

