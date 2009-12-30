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
            count = len(list(fs.managed_targets()))
            servers = fs.managed_target_servers()
            print "Starting %d targets of %s on %s" % (count,
                    fs.fs_name, servers)

    def handle_post(self, fs):
        if self.verbose > 0:
            Status.status_view_fs(fs, show_clients=False)

    def ev_starttarget_start(self, node, target):
        # start/restart timer if needed (we might be running a new runloop)
        if self.verbose > 1:
            print "%s: Starting %s %s (%s)..." % (node, \
                    target.type.upper(), target.get_id(), target.dev)
        self.update()

    def ev_starttarget_done(self, node, target):
        self.status_changed = True
        if self.verbose > 1:
            if target.status_info:
                print "%s: Start of %s %s (%s): %s" % \
                        (node, target.type.upper(), target.get_id(), target.dev,
                                target.status_info)
            else:
                print "%s: Start of %s %s (%s) succeeded" % \
                        (node, target.type.upper(), target.get_id(), target.dev)
        self.update()

    def ev_starttarget_failed(self, node, target, rc, message):
        self.status_changed = True
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to start %s %s (%s): %s" % \
                (node, target.type.upper(), target.get_id(), target.dev,
                        strerr)
        if rc:
            print message
        self.update()


class LocalStartEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=1):
        self.verbose = verbose

    def ev_starttarget_start(self, node, target):
        if self.verbose > 1:
            print "Starting %s %s (%s)..." % (target.type.upper(),
                    target.get_id(), target.dev)

    def ev_starttarget_done(self, node, target):
        if self.verbose > 1:
            if target.status_info:
                print "Start of %s %s (%s): %s" % (target.type.upper(),
                        target.get_id(), target.dev, target.status_info)
            else:
                print "Start of %s %s (%s) succeeded" % (target.type.upper(),
                        target.get_id(), target.dev)

    def ev_starttarget_failed(self, node, target, rc, message):
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "Failed to start %s %s (%s): %s" % (target.type.upper(),
                target.get_id(), target.dev, strerr)
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
                    indexes=self.indexes_support.get_rangeset(),
                    labels=self.target_support.get_labels(),
                    event_handler=eh)

            # Prepare options...
            mount_options = {}
            mount_paths = {}
            for target_type in [ 'mgt', 'mdt', 'ost' ]:
                mount_options[target_type] = fs_conf.get_target_mount_options(target_type)
                mount_paths[target_type] = fs_conf.get_target_mount_path(target_type)

            fs.set_debug(self.debug_support.has_debug())

            # Warn if trying to act on wrong nodes
            if not self.nodes_support.check_valid_list(fsname, \
                    fs.managed_target_servers(), "start"):
                result = RC_FAILURE
                continue

            # Will call the handle_pre() method defined by the event handler.
            if hasattr(eh, 'pre'):
                eh.pre(fs)
                
            status = fs.start(mount_options=mount_options,
                              mount_paths=mount_paths)

            rc = self.fs_status_to_rc(status)
            if rc > result:
                result = rc

            if rc == RC_OK:
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
                for nodes, msg in fs.proxy_errors:
                    print "%s: %s" % (nodes, msg)

            if hasattr(eh, 'post'):
                eh.post(fs)

        return result
