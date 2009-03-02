# Stop.py -- Stop file system
# Copyright (C) 2007, 2008, 2009 CEA
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

from Shine.FSUtils import open_lustrefs

from Base.RemoteCommand import RemoteCommand
from Base.Support.FS import FS
from Base.Support.Indexes import Indexes
from Base.Support.Nodes import Nodes
from Base.Support.Target import Target
from Base.Support.Quiet import Quiet
from RemoteCallEventHandler import RemoteCallEventHandler

import Shine.Lustre.EventHandler

import os
import socket

class GlobalStopEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.failures = 0
        self.success = 0

    def ev_stoptarget_start(self, node, target):
        if self.verbose:
            print "%s: Stopping %s %s (%s)..." % (node, \
                    target.type.upper(), target.get_id(), target.dev)

    def ev_stoptarget_done(self, node, target):
        self.success += 1
        if self.verbose:
            if target.status_info:
                print "%s: Stop of %s %s (%s): %s" % \
                        (node, target.type.upper(), target.get_id(), target.dev,
                                target.status_info)
            else:
                print "%s: Stop of %s %s (%s) succeeded" % \
                        (node, target.type.upper(), target.get_id(), target.dev)

    def ev_stoptarget_failed(self, node, target, rc, message):
        self.failures += 1
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to stop %s %s (%s): %s" % \
                (node, target.type.upper(), target.get_id(), target.dev,
                        strerr)
        if rc:
            print message

    def complete(self):
        if self.failures == 0:
            print "Stop successful."
            return 0
        else:
            if self.failures == 1:
                print "Stop failed (%d error)" % self.failures
            else:
                print "Stop failed (%d errors)" % self.failures
            return 1





class Stop(RemoteCommand):
    """
    shine stop -f <filesystem>
    """

    def __init__(self):
        RemoteCommand.__init__(self)

        self.fs_support = FS(self)
        self.indexes_support = Indexes(self)
        self.nodes_support = Nodes(self)
        self.target_support = Target(self)
        self.quiet_support = Quiet(self)


    def get_name(self):
        return "stop"

    def get_desc(self):
        return "Stop file system servers."

    def execute(self):

        if self.local_flag or self.remote_call:
            self.opt_n = socket.gethostname()

        target = self.target_support.get_target()
        for fsname in self.fs_support.iter_fsname():

            if self.remote_call:
                handler = RemoteCallEventHandler()
            elif self.local_flag:
                handler = LocalStopEventHandler(not self.opt_q)
            else:
                handler = GlobalStopEventHandler(not self.opt_q)

            fs_conf, fs = open_lustrefs(fsname, target,
                    nodes=self.nodes_support.get_nodeset(),
                    indexes=self.indexes_support.get_rangeset(),
                    event_handler=handler)

            mount_options = {}
            mount_paths = {}
            for target_type in [ 'mgt', 'mdt', 'ost' ]:
                mount_options[target_type] = fs_conf.get_target_mount_options(target_type)
                mount_paths[target_type] = fs_conf.get_target_mount_path(target_type)

            fs.set_debug(self.debug_support.has_debug())

            fs.stop()

            if not self.remote_call:
                return handler.complete()

