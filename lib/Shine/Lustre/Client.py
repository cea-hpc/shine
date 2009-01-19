# Client.py -- Lustre Client (pseudo target)
# Copyright (C) 2008 CEA
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
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker

from Target import Target

from Shine.Commands.CommandRegistry import CommandRegistry


class Client(NodeSet):
    
    def __init__(self, node, mntp, fs):
        NodeSet.__init__(self, node)
        self.fs = fs
        self.mntp = mntp

    def test(self):
        print "test CLIENT %s" % self

    def start(self):
        #self._mount()
        pass

    def stop(self):
        #self._umount()
        pass

    def status(self):
        # Check Lustre Health
        try:
            f = open("/proc/fs/lustre/health_check")
            if not f.readline().startswith("healthy"):
                CommandRegistry.output(fs=self.fs.fs_name, node=self[0],
                        health=f.read())
            f.close()
        except IOError, (errno, strerror):
            CommandRegistry.output(fs=self.fs.fs_name, node=self[0],
                        health=strerror, err=errno)
        except Exception, e:
            print e


        # Check Mounts
        sta = "UNKNOWN"
        f = open("/proc/mounts")
        try:
            mntps = [line for line in f if line.find("%s lustre" % self.mntp) >= 0]
            if len(mntps) == 0:
                sta = "NOT MOUNTED"
            elif len(mntps) > 1:
                sta = "MULTIPLE MOUNTS"
            else:
                sta = "MOUNTED"
        finally:
            f.close()
        
        CommandRegistry.output(fs=self.fs.fs_name, node=self[0],
                mount=self.mntp, status_client=sta)

    def format(self):
        pass
        #self.fs.push_action(Format(Task.current(), self.fs, self))

    def fcsk(self):
        pass

