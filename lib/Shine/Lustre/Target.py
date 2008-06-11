# Target.py -- Lustre Target base class
# Copyright (C) 2007, 2008 CEA
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

from Actions.Format import Format
from Actions.Mount import Mount
from Actions.Umount import Umount

from Shine.Commands.CommandRegistry import CommandRegistry

import binascii
import os 
import pickle
import stat
import sys

class TargetOpInProgressException(Exception):
    pass

class TargetException(Exception):
    def __init__(self, target):
        self.target = target

class TargetNotMountedError(TargetException):
    def __str__(self):
        return "%s %s (%s) [NOT MOUNTED]" % (self.target.type, self.target.name, self.target.dev)

class TargetMultiMountedError(TargetException):
    def __str__(self):
        return "%s %s (%s) [MULTIPLE MOUNTS]" % (self.target.type, self.target.name, self.target.dev)


class Target(NodeSet):

    def __init__(self, cf_target, fs):
        NodeSet.__init__(self, cf_target.get_nodename())

        # MGT, MDT, OST or CLIENT
        self.type = cf_target.get_type()

        # Other target config parameters
        self.tag = cf_target.get_tag()
        self.dev = cf_target.get_dev()
        self.dev_size = cf_target.get_dev_size()
        self.jdev = cf_target.get_jdev()
        self.jdev_size = cf_target.get_jdev_size()

        # Define target mount point
        self.mntp = "/mnt/%s/%s" % (fs.fs_name, self.tag)

        self.fs = fs
        self.worker = None

        # Status vars
        self.index = 0

        # Build target label
        self.label = "%s-%s%04x" % (self.fs.fs_name, self.type, self.index)

    def is_mgt(self):
        return self.type == 'MGT'

    def is_mdt(self):
        return self.type == 'MDT'

    def is_ost(self):
        return self.type == 'OST'

    def _mount(self):
        action = Mount(Task.current(), self.fs, self)
        action.launch()

    def _umount(self):
        action = Umount(Task.current(), self.fs, self)
        action.launch()

    def set_status(self, new_cfg_status):
        pass
        #self.fs.config.set_target_status(self.tag,
        #                                 status="offline",
        #                                 cfg_status=new_cfg_status,
        #                                 fs_name=self.fs.fs_name)

    def start(self):
        pass

    def stop(self):
        pass

    def status(self):
        # Wrong status if the device doesn't exist

        mode = os.stat(self.dev)[stat.ST_MODE]
        if not stat.S_ISBLK(mode):
            raise TargetBlockDeviceNotFoundError(self)

        sta = "UNKNOWN"
        f = open("/proc/mounts")
        try:
            mntps = [line for line in f if line.find("%s lustre" % self.mntp) >= 0]
            if len(mntps) == 0:
                sta = "NOT MOUNTED"
                #raise TargetNotMountedError(self)
            elif len(mntps) > 1:
                sta = "MULTIPLE MOUNTS"
                #raise TargetMultiMountedError(self)
            else:
                sta = "MOUNTED"
                #"/proc/fs/lustre/mdt/testfs-MDT0000/recovery_status"
            
        finally:
            f.close()
        
        CommandRegistry.output(type=self.type, tag=self.tag, dev=self.dev,
            status=sta)

    def format(self):
        self.fs.push_action(Format(Task.current(), self.fs, self))

    def fcsk(self):
        pass

