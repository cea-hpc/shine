# Umount.py -- Unmount file system on clients
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
Shine `umount' command classes.

The umount command aims to stop Lustre filesystem clients.
"""

import os

# Configuration
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

# Command base class
from Base.FSClientLiveCommand import FSClientLiveCommand
from Base.CommandRCDefs import *
# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler

# Command helper
from Shine.FSUtils import open_lustrefs

# Lustre events
import Shine.Lustre.EventHandler
from Shine.Lustre.FileSystem import *


class GlobalUmountEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=1):
        self.verbose = verbose

    def ev_stopclient_start(self, node, client):
        if self.verbose > 1:
            print "%s: Unmounting %s on %s ..." % (node, client.fs.fs_name, client.mount_path)

    def ev_stopclient_done(self, node, client):
        if self.verbose > 1:
            if client.status_info:
                print "%s: Umount: %s" % (node, client.status_info)
            else:
                print "%s: FS %s succesfully unmounted from %s" % (node,
                        client.fs.fs_name, client.mount_path)

    def ev_stopclient_failed(self, node, client, rc, message):
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to unmount FS %s from %s: %s" % \
                (node, client.fs.fs_name, client.mount_path, strerr)
        if rc:
            print message


class Umount(FSClientLiveCommand):
    """
    shine umount
    """

    def __init__(self):
        FSClientLiveCommand.__init__(self)

    def get_name(self):
        return "umount"

    def get_desc(self):
        return "Unmount file system clients."

    target_status_rc_map = { \
            MOUNTED : RC_FAILURE,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def fs_status_to_rc(self, status):
        return self.target_status_rc_map[status]

    def execute(self):
        result = 0

        self.init_execute()

        # Get verbose level.
        vlevel = self.verbose_support.get_verbose_level()

        for fsname in self.fs_support.iter_fsname():

            # Install appropriate event handler.
            eh = self.install_eventhandler(None,
                    GlobalUmountEventHandler(vlevel))

            nodes = self.nodes_support.get_nodeset()

            fs_conf, fs = open_lustrefs(fsname, None,
                    nodes=nodes,
                    indexes=None,
                    event_handler=eh)

            if nodes and not nodes.issubset(fs_conf.get_client_nodes()):
                raise CommandException("%s are not client nodes of filesystem '%s'" % \
                        (nodes - fs_conf.get_client_nodes(), fsname))

            fs.set_debug(self.debug_support.has_debug())

            status = fs.umount()
            rc = self.fs_status_to_rc(status)
            if rc > result:
                result = rc

            if rc == RC_OK:
                if vlevel > 0:
                    print "Unmount successful."
            elif rc == RC_RUNTIME_ERROR:
                for nodes, msg in fs.proxy_errors:
                    print "%s: %s" % (nodes, msg)

        return result

