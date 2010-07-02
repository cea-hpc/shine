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

# Configuration
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

# Command base class
from Base.FSClientLiveCommand import FSClientLiveCommand
from Base.CommandRCDefs import *
# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler

from Exceptions import CommandException

# Command helper
from Shine.FSUtils import open_lustrefs
from Shine.Commands.Tune import Tune

# Lustre events
from Base.FSEventHandler import FSGlobalEventHandler
import Shine.Lustre.EventHandler
from Shine.Lustre.FileSystem import *

class GlobalMountEventHandler(FSGlobalEventHandler):

    def handle_pre(self, fs):
        if self.verbose > 0:
            count = len(list(fs.managed_components(supports='mount')))
            servers = fs.managed_component_servers(supports='mount')
            print "Starting %d client(s) of %s on %s" % (count,
                    fs.fs_name, servers)

    def handle_post(self, fs):
        pass

    def ev_mountclient_start(self, node, comp):
        if self.verbose > 1:
            print "%s: Mounting %s on %s ..." % (node, comp.fs.fs_name, comp.mount_path)
        self.update()

    def ev_mountclient_done(self, node, comp):
        self.update_client_status(node, "succeeded")

        if self.verbose > 1:
            if comp.status_info:
                print "%s: Mount %s: %s" % (node, comp.fs.fs_name, comp.status_info)
            else:
                print "%s: FS %s succesfully mounted on %s" % (node,
                        comp.fs.fs_name, comp.mount_path)
        self.update()

    def ev_mountclient_failed(self, node, comp, rc, message):
        self.update_client_status(node, "failed")

        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to mount FS %s on %s: %s" % \
                (node, comp.fs.fs_name, comp.mount_path, strerr)
        if rc:
            print message

        self.update()

    def set_fs_config(self, fs_conf):
        self.fs_conf = fs_conf

    def update_client_status(self, client_name, status):
        # Change the status of client 
        if status == "succeeded":
            self.fs_conf.set_status_clients_mount_complete([client_name], None)
        elif status == "failed":
            self.fs_conf.set_status_clients_mount_failed([client_name], None)

class Mount(FSClientLiveCommand):
    """
    """

    def __init__(self):
        FSClientLiveCommand.__init__(self)

    def get_name(self):
        return "mount"

    def get_desc(self):
        return "Mount file system clients."

    target_status_rc_map = { \
            MOUNTED : RC_OK,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_FAILURE,
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
                    GlobalMountEventHandler(vlevel))

            # Get filesystem informations
            fs_conf, fs = open_lustrefs(fsname, None,
                    nodes=self.nodes_support.get_nodeset(),
                    indexes=None,
                    excluded=self.nodes_support.get_excludes(),
                    labels=self.label_support.get_labels(),
                    event_handler=eh)

            if not self.has_local_flag():
                # Allow global handler to access fs_conf.
                eh.set_fs_config(fs_conf)

            # Enabled debugging if debug flag was set on CLI.
            fs.set_debug(self.debug_support.has_debug())

            # Warn if trying to act on wrong nodes
            if not self.nodes_support.check_valid_list(fsname, \
                    fs.managed_component_servers(supports='mount'), "mount"):
                result = RC_FAILURE
                continue

            # Will call the handle_pre() method defined by the event handler.
            if hasattr(eh, 'pre'):
                eh.pre(fs)

            status = fs.mount(mount_options=fs_conf.get_mount_options(), 
                              addopts=self.addopts.get_options())

            rc = self.fs_status_to_rc(status)
            if rc > result:
                result = rc

            if not self.remote_call:
                if rc == RC_OK:
                    # Notify backend of file system status mofication
                    fs_conf.set_status_fs_mounted()

                    if vlevel > 0:
                        key = lambda c: c.state == MOUNTED
                        print "Mount successful on %s" % \
                            fs.managed_component_servers(supports='mount',filter_key=key)

                    # Apply tuning after successful mount(s)
                    tuning = Tune.get_tuning(fs_conf)
                    status = fs.tune(tuning)
                    if status == MOUNTED:
                        print "Filesystem tuning applied on %s" % \
                            fs.managed_component_servers(supports='mount')
                    elif status == RUNTIME_ERROR:
                        rc = RC_RUNTIME_ERROR

                        # Notify backend of file system status mofication
                        fs_conf.set_status_fs_warning()

                        for nodes, msg in fs.proxy_errors:
                            print "%s: %s" % (nodes, msg)
                else:
                    # Display a failure message in case of previous failed
                    # mounts. For now, if one mount fail, the tuning is
                    # skipped. Use `shine tune' to manually tune the FS.
                    # Trac ticket #46 aims to improve this.
                    if vlevel > 0:
                        print "Tuning skipped!"
                    if rc == RC_RUNTIME_ERROR:
                        for nodes, msg in fs.proxy_errors:
                            print "%s: %s" % (nodes, msg)

            if hasattr(eh, 'post'):
                eh.post(fs)

        return result
