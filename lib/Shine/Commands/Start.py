# Start.py -- Start file system
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
Shine `start' command classes.

The start command aims to start Lustre filesystem servers or just some
of the filesystem targets on local or remote servers. It is available
for any filesystems previously installed and formatted.
"""

import os

# Configuration
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

from Shine.Commands.Status import Status
from Shine.Commands.Tune import Tune

# Command base class
from Base.FSLiveCommand import FSLiveCommand
from Base.FSEventHandler import FSGlobalEventHandler
from Base.CommandRCDefs import *
# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler

# Command helper
from Shine.FSUtils import open_lustrefs

# Lustre events
import Shine.Lustre.EventHandler

# Shine Proxy Protocol
from Shine.Lustre.Actions.Proxies.ProxyAction import *
from Shine.Lustre.FileSystem import *


class GlobalStartEventHandler(FSGlobalEventHandler):

    def __init__(self, verbose=1):
        FSGlobalEventHandler.__init__(self, verbose)

    def handle_pre(self, fs):
        if self.verbose > 0:
            count = len(list(fs.managed_components(supports='start')))
            servers = fs.managed_component_servers(supports='start')
            print "Starting %d component(s) of %s on %s" % (count,
                    fs.fs_name, servers)

    def handle_post(self, fs):
        if self.verbose > 0:
            Status.status_view_fs(fs, show_clients=False)

    def ev_starttarget_start(self, node, comp):
        self.update_config_status(comp, "starting")
        # start/restart timer if needed (we might be running a new runloop)
        if self.verbose > 1:
            print "%s: Starting %s (%s)..." % (node, \
                    comp.get_id(), comp.dev)
        self.update()

    def ev_starttarget_done(self, node, comp):
        self.update_config_status(comp, "succeeded")
        self.status_changed = True
        if self.verbose > 1:
            if comp.status_info:
                print "%s: Start of %s (%s): %s" % \
                       (node, comp.get_id(), comp.dev, comp.status_info)
            else:
                print "%s: Start of %s (%s) succeeded" % \
                       (node, comp.get_id(), comp.dev)
        self.update()

    def ev_starttarget_failed(self, node, comp, rc, message):
        self.update_config_status(comp, "failed")

        self.status_changed = True
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to start %s (%s): %s" % \
               (node, comp.get_id(), comp.dev, strerr)
        if rc:
            print message
        self.update()

    def ev_startrouter_start(self, node, comp):
        if self.verbose > 1:
            print "%s: Starting router..." % node
        self.update()

    def ev_startrouter_done(self, node, comp):
        self.status_changed = True
        if self.verbose > 1:
            if comp.status_info:
                print "%s: Start of router: %s" % \
                       (node, comp.status_info)
            else:
                print "%s: Start of router succeeded" % node
        self.update()

    def ev_startrouter_failed(self, node, comp, rc, message):
        self.status_changed = True
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to start router: %s" % \
               (node, strerr)
        if rc:
            print message
        self.update()

    def set_fs_config(self, fs_conf):
        self.fs_conf = fs_conf

    def update_config_status(self, target, status):
        # Retrieve the right target from the configuration
        target_list = [self.fs_conf.get_target_from_tag_and_type(target.tag,
            target.TYPE.upper())]

        # Change the status of targets to register their running state
        if status == "succeeded":
            self.fs_conf.set_status_targets_online(target_list, None)
        elif status == "failed":
            self.fs_conf.set_status_targets_offline(target_list, None)
        else:
            self.fs_conf.set_status_targets_starting(target_list, None)

class LocalStartEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=1):
        self.verbose = verbose

    def ev_starttarget_start(self, node, comp):
        if self.verbose > 1:
            print "Starting %s (%s)..." % \
                   (comp.get_id(), comp.dev)

    def ev_starttarget_done(self, node, comp):
        if self.verbose > 1:
            if comp.status_info:
                print "Start of %s (%s): %s" % \
                       (comp.get_id(), comp.dev, comp.status_info)
            else:
                print "Start of %s (%s) succeeded" % \
                       (comp.get_id(), comp.dev)

    def ev_starttarget_failed(self, node, comp, rc, message):
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "Failed to start %s (%s): %s" % \
               (comp.get_id(), comp.dev, strerr)
        if rc:
            print message

    def ev_startrouter_start(self, node, comp):
        if self.verbose > 1:
            print "Starting router..."

    def ev_startrouter_done(self, node, comp):
        if self.verbose > 1:
            if comp.status_info:
                print "Start of router: %s" % comp.status_info
            else:
                print "Start of router succeeded"

    def ev_startrouter_failed(self, node, comp, rc, message):
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "Failed to start router: %s" % strerr
        if rc:
            print message


class Start(FSLiveCommand):
    """
    shine start [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-qv]
    """

    def __init__(self):
        FSLiveCommand.__init__(self)

    def get_name(self):
        return "start"

    def get_desc(self):
        return "Start file system servers."

    target_status_rc_map = { \
            MOUNTED : RC_OK,
            RECOVERING : RC_OK,
            EXTERNAL : RC_ST_EXTERNAL,
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

        target = self.target_support.get_target()
        for fsname in self.fs_support.iter_fsname():

            # Install appropriate event handler.
            eh = self.install_eventhandler(LocalStartEventHandler(vlevel),
                    GlobalStartEventHandler(vlevel))

            # Open configuration and instantiate a Lustre FS.
            fs_conf, fs = open_lustrefs(fsname, target,
                    nodes=self.nodes_support.get_nodeset(),
                    excluded=self.nodes_support.get_excludes(),
                    failover=self.target_support.get_failover(),
                    indexes=self.indexes_support.get_rangeset(),
                    labels=self.label_support.get_labels(),
                    event_handler=eh)

            if not self.has_local_flag():
                # Allow global handler to access fs_conf.
                eh.set_fs_config(fs_conf)

            # Prepare options...
            mount_options = {}
            mount_paths = {}
            for target_type in [ 'mgt', 'mdt', 'ost' ]:
                mount_options[target_type] = fs_conf.get_target_mount_options(target_type)
                mount_paths[target_type] = fs_conf.get_target_mount_path(target_type)

            fs.set_debug(self.debug_support.has_debug())

            # Ignore all clients for this command
            fs.disable_clients()

            # Warn if trying to act on wrong nodes
            if not self.nodes_support.check_valid_list(fsname, \
                    fs.managed_component_servers(supports='start'), "start"):
                result = RC_FAILURE
                continue

            # Will call the handle_pre() method defined by the event handler.
            if hasattr(eh, 'pre'):
                eh.pre(fs)
                
            # Notify backend of file system status mofication
            fs_conf.set_status_fs_starting()

            status = fs.start(mount_options=mount_options,
                              mount_paths=mount_paths,
                              addopts=self.addopts.get_options(),
                              failover=self.target_support.get_failover())

            rc = self.fs_status_to_rc(status)
            if rc > result:
                result = rc

            if rc == RC_OK:
                # Notify backend of file system status mofication
                fs_conf.set_status_fs_online()

                if vlevel > 0:
                    print "Start successful."
                tuning = Tune.get_tuning(fs_conf)
                status = fs.tune(tuning)
                if status == RUNTIME_ERROR:
                    rc = RC_RUNTIME_ERROR
                # XXX improve tuning on start error handling
            elif vlevel > 0:
                print "Tuning skipped."

            if rc == RC_RUNTIME_ERROR:
                # Notify backend of file system status mofication
                fs_conf.set_status_fs_online_failed()

                for nodes, msg in fs.proxy_errors:
                    print "%s: %s" % (nodes, msg)

            if hasattr(eh, 'post'):
                eh.post(fs)

        return result
