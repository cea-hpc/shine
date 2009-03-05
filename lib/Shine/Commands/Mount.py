# Mount.py -- Mount file system on clients
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
Shine `mount' command classes.

The mount command aims to start Lustre filesystem clients.
"""

import os
import socket

# Configuration
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

# Command base class
from Base.FSClientLiveCommand import FSClientLiveCommand
# -R handler
from RemoteCallEventHandler import RemoteCallEventHandler

from Exceptions import CommandException

# Command helper
from Shine.FSUtils import open_lustrefs

# Lustre events
import Shine.Lustre.EventHandler


class GlobalMountEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.failures = 0
        self.success = 0

    def ev_startclient_start(self, node, client):
        if self.verbose:
            print "%s: Mounting %s on %s ..." % (node, client.fs.fs_name, client.mount_path)

    def ev_startclient_done(self, node, client):
        self.success += 1
        if self.verbose:
            if client.status_info:
                print "%s: Mount: %s" % (node, client.status_info)
            else:
                print "%s: FS %s succesfully mounted on %s" % (node,
                        client.fs.fs_name, client.mount_path)

    def ev_startclient_failed(self, node, client, rc, message):
        self.failures += 1
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to mount FS %s on %s: %s" % \
                (node, client.fs.fs_name, client.mount_path, strerr)
        if rc:
            print message

    def complete(self):
        if self.failures == 0:
            print "Mount successful."
            return 0
        else:
            if self.failures == 1:
                print "Mount failed (%d error)" % self.failures
            else:
                print "Mount failed (%d errors)" % self.failures
            return 1



class Mount(FSClientLiveCommand):
    """
    """

    def __init__(self):
        FSClientLiveCommand.__init__(self)

    def get_name(self):
        return "mount"

    def get_desc(self):
        return "Mount file system clients."

    def execute(self):

        if self.local_flag or self.remote_call:
            self.opt_n = socket.gethostname()

        for fsname in self.fs_support.iter_fsname():

            if self.remote_call:
                handler = RemoteCallEventHandler()
            elif self.local_flag:
                handler = LocalMountEventHandler(not self.opt_q)
            else:
                handler = GlobalMountEventHandler(not self.opt_q)

            nodes = self.nodes_support.get_nodeset()

            fs_conf, fs = open_lustrefs(fsname, None,
                    nodes=self.nodes_support.get_nodeset(),
                    indexes=None,
                    event_handler=handler)

            if nodes and not nodes.issubset(fs_conf.get_client_nodes()):
                raise CommandException("%s are not client nodes of filesystem '%s'" % \
                        (nodes - fs_conf.get_client_nodes(), fsname))

            fs.set_debug(self.debug_support.has_debug())

            fs.mount()

            if not self.remote_call:
                return handler.complete()

