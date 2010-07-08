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

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSLiveCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, \
                                              RC_FAILURE, RC_TARGET_ERROR, \
                                              RC_CLIENT_ERROR, RC_RUNTIME_ERROR
# Lustre events
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler

from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, OFFLINE, \
                                    TARGET_ERROR, CLIENT_ERROR, RUNTIME_ERROR


class GlobalUmountEventHandler(FSGlobalEventHandler):

    def handle_pre(self, fs):
        if self.verbose > 0:
            count = len(list(fs.managed_components(supports='umount')))
            servers = fs.managed_component_servers(supports='umount')
            print "Stopping %d client(s) of %s on %s" % (count,
                    fs.fs_name, servers)

    def handle_post(self, fs):
        pass

    def ev_umountclient_start(self, node, comp):
        if self.verbose > 1:
            print "%s: Unmounting %s on %s ..." % (node, comp.fs.fs_name, comp.mount_path)
        self.update()

    def ev_umountclient_done(self, node, comp):
        self.update_client_status(node, "succeeded")

        if self.verbose > 1:
            if comp.status_info:
                print "%s: Umount %s: %s" % (node, comp.fs.fs_name, comp.status_info)
            else:
                print "%s: FS %s succesfully unmounted from %s" % (node,
                        comp.fs.fs_name, comp.mount_path)
        self.update()

    def ev_umountclient_failed(self, node, comp, rc, message):
        self.update_client_status(node, "failed")

        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to unmount FS %s from %s: %s" % \
                (node, comp.fs.fs_name, comp.mount_path, strerr)
        if rc:
            print message

        self.update()

    def update_client_status(self, client_name, status):
        # Change the status of client 
        if status == "succeeded":
            self.fs_conf.set_status_clients_umount_complete([client_name], None)
        elif status == "failed":
            self.fs_conf.set_status_clients_umount_failed([client_name], None)


class Umount(FSLiveCommand):
    """
    shine umount
    """

    NAME = "umount"
    DESCRIPTION = "Unmount file system clients."

    GLOBAL_EH = GlobalUmountEventHandler
    LOCAL_EH = None

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_FAILURE,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        if not self.nodes_support.check_valid_list(fs.fs_name, \
                fs.managed_component_servers('umount'), "unmount"):
            return RC_FAILURE

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        status = fs.umount(addopts=self.addopts.get_options())

        rc = self.fs_status_to_rc(status)

        if not self.remote_call:
            if rc == RC_OK:
                
                # Is there mounted clients ?
                client_status_dict = fs_conf.get_status_clients()
                nb_mounted_clients = len([ node_name for node_name in client_status_dict if client_status_dict[node_name]['status'] == 'm_complete'])
                if nb_mounted_clients == 0:
                    # No
                    # all client nodes have been umounted successfuly
                    fs_conf.set_status_fs_online()
                if vlevel > 0:
                    key = lambda c: c.state == OFFLINE
                    print "Unmount successful on %s" % \
                        fs.managed_component_servers('umount', filter_key=key)
            elif rc == RC_RUNTIME_ERROR:
                for nodes, msg in fs.proxy_errors:
                    print "%s: %s" % (nodes, msg)

        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
