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

"""
Shine `stop' command classes.

The stop command aims to stop Lustre filesystem servers or just some
of the filesystem targets on local or remote servers. It is available
for any filesystems previously installed and formatted.
"""

import os
import socket

# Configuration
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

# Command base class
from Base.FSLiveCommand import FSLiveCommand
# -R handler
from RemoteCallEventHandler import RemoteCallEventHandler

# Command helper
from Shine.FSUtils import open_lustrefs

# Lustre events
import Shine.Lustre.EventHandler


class GlobalStopEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=False):
        self.verbose = verbose

    def ev_stoptarget_start(self, node, target):
        if self.verbose:
            print "%s: Stopping %s %s (%s)..." % (node, \
                    target.type.upper(), target.get_id(), target.dev)

    def ev_stoptarget_done(self, node, target):
        if self.verbose:
            if target.status_info:
                print "%s: Stop of %s %s (%s): %s" % \
                        (node, target.type.upper(), target.get_id(), target.dev,
                                target.status_info)
            else:
                print "%s: Stop of %s %s (%s) succeeded" % \
                        (node, target.type.upper(), target.get_id(), target.dev)

    def ev_stoptarget_failed(self, node, target, rc, message):
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to stop %s %s (%s): %s" % \
                (node, target.type.upper(), target.get_id(), target.dev,
                        strerr)
        if rc:
            print message


class Stop(FSLiveCommand):
    """
    shine stop [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-qv]
    """

    def __init__(self):
        FSLiveCommand.__init__(self)

    def get_name(self):
        return "stop"

    def get_desc(self):
        return "Stop file system servers."

    def execute(self):

        if self.local_flag or self.remote_call:
            self.opt_n = socket.gethostname().split('.', 1)[0]

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

            ok = fs.stop()

            if self.remote_call:
                # Remote call: lustre errors handled by caller.
                return 0

            if ok:
                if not self.quiet_support.has_quiet():
                    print "Stop successful."
                return 0
            else:
                if not self.quiet_support.has_quiet():
                    print "Stop failed."
                return 1

