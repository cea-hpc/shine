# Format.py -- Format file system targets
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

from Status import Status
from Exceptions import *

from Base.FSLiveCommand import FSLiveCriticalCommand
from Base.FSEventHandler import FSGlobalEventHandler
from Base.CommandRCDefs import *
# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler


from Shine.FSUtils import open_lustrefs

# timer events
import ClusterShell.Event

# lustre events
import Shine.Lustre.EventHandler

# Shine Proxy Protocol
from Shine.Lustre.Actions.Proxies.ProxyAction import *
from Shine.Lustre.FileSystem import *

from ClusterShell.NodeSet import *
from ClusterShell.Task import task_self

import datetime
import socket
import sys


class GlobalFormatEventHandler(FSGlobalEventHandler):

    def __init__(self, verbose=1):
        FSGlobalEventHandler.__init__(self, verbose)

    def handle_pre(self, fs):
        # attach fs to this handler
        if self.verbose > 0:
            print "Starting format of %d targets on %s" % (fs.target_count,
                    fs.target_servers)

    def handle_post(self, fs):
        if self.verbose > 0:
            Status.status_view_fs(fs, show_clients=False)

    def ev_formatjournal_start(self, node, target):
        if self.verbose > 1:
            print "%s: Starting format of %s %s journal (%s)" % (node, \
                    target.type.upper(), target.get_id(), target.jdev)

    def ev_formatjournal_done(self, node, target):
        if self.verbose > 1:
            print "%s: Format of %s %s journal (%s) succeeded" % \
                    (node, target.type.upper(), target.get_id(), target.jdev)

    def ev_formatjournal_failed(self, node, target, rc, message):
        print "%s: Format of %s %s journal (%s) failed with error %d" % \
                (node, target.type.upper(), target.get_id(), target.jdev, rc)
        print message

    def ev_format_start(self, node, target, **kwargs):
        self.update_config_status(target, "formatting")

        if self.verbose > 1:
            print "%s: Starting format of %s %s (%s)" % (node, target.type.upper(), \
                    target.get_id(), target.dev)

        self.update()

    def ev_format_done(self, node, target):
        self.update_config_status(target, "succeeded")

        if self.verbose > 1:
            print "%s: Format of %s %s (%s) succeeded" % \
                    (node, target.type.upper(), target.get_id(), target.dev)

        self.update()

    def ev_format_failed(self, node, target, rc, message):
        self.update_config_status(target, "failed")

        print "%s: Format of %s %s (%s) failed with error %d" % \
                (node, target.type.upper(), target.get_id(), target.dev, rc)
        print message

        self.update()

    def set_fs_config(self, fs_conf):
        self.fs_conf = fs_conf

    def update_config_status(self, target, status):
        # Retrieve the right target from the configuration
        target_list = [self.fs_conf.get_target_from_tag_and_type(target.tag,
            target.type.upper())]

        # Change the status of targets to avoid their use
        # in an other file system
        if status == "succeeded":
            self.fs_conf.set_status_targets_formated(target_list, None)
        elif status == "failed":
            self.fs_conf.set_status_targets_format_failed(target_list, None)
        else:
            self.fs_conf.set_status_targets_formating(target_list, None)


class LocalFormatEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=1):
        self.verbose = verbose
        self.failures = 0
        self.success = 0

    def ev_formatjournal_start(self, node, target):
        print "Starting format of %s %s journal (%s)" % (target.type.upper(), \
                target.get_id(), target.jdev)

    def ev_formatjournal_done(self, node, target):
        print "Format of %s %s journal (%s) succeeded" % \
                (target.type.upper(), target.get_id(), target.jdev)

    def ev_formatjournal_failed(self, node, target, rc, message):
        self.failures += 1
        print "Format of %s %s journal (%s) failed with error %d" % \
                (target.type.upper(), target.get_id(), target.jdev, rc)
        print message

    def ev_format_start(self, node, target):
        print "Starting format of %s %s (%s)" % (target.type.upper(), \
                target.get_id(), target.dev)
        sys.stdout.flush()

    def ev_format_done(self, node, target):
        self.success += 1
        print "Format of %s %s (%s) succeeded" % \
                (target.type.upper(), target.get_id(), target.dev)

    def ev_format_failed(self, node, target, rc, message):
        self.failures += 1
        print "Format of %s %s (%s) failed with error %d" % \
                (target.type.upper(), target.get_id(), target.dev, rc)
        print message


class Format(FSLiveCriticalCommand):
    """
    shine format -f <fsname> [-t <target>] [-i <index(es)>] [-n <nodes>]
    """
    
    def __init__(self):
        FSLiveCriticalCommand.__init__(self)

    def get_name(self):
        return "format"

    def get_desc(self):
        return "Format file system targets."

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

        # Do not allow implicit filesystems format.
        if not self.opt_f:
            raise CommandHelpException("A filesystem is required (use -f).", self)

        # Initialize remote command specifics.
        self.init_execute()

        # Setup verbose level.
        vlevel = self.verbose_support.get_verbose_level()

        target = self.target_support.get_target()
        for fsname in self.fs_support.iter_fsname():

            # Install appropriate event handler.
            eh = self.install_eventhandler(LocalFormatEventHandler(vlevel),
                    GlobalFormatEventHandler(vlevel))

            # Open configuration and instantiate a Lustre FS.
            fs_conf, fs = open_lustrefs(fsname, target,
                    nodes=self.nodes_support.get_nodeset(),
                    indexes=self.indexes_support.get_rangeset(),
                    event_handler=eh)

            if not self.has_local_flag():
                # Allow global handler to access fs_conf.
                eh.set_fs_config(fs_conf)

            # Prepare options...
            fs.set_debug(self.debug_support.has_debug())

            if not self.ask_confirm("Format %s on %s: are you sure?" % (fsname,
                    fs.get_enabled_target_servers())):
                result = RC_FAILURE
                continue

            mkfs_options = {}
            format_params = {}
            for target_type in [ 'mgt', 'mdt', 'ost' ]:
                format_params[target_type] = \
                        fs_conf.get_target_format_params(target_type)
                mkfs_options[target_type] = \
                        fs_conf.get_target_mkfs_options(target_type) 

            # Call a pre_format method if defined by the event handler.
            if hasattr(eh, 'pre'):
                eh.pre(fs)
            
            # Format really.
            status = fs.format(stripecount=fs_conf.get_stripecount(),
                        stripesize=fs_conf.get_stripesize(),
                        format_params=format_params,
                        mkfs_options=mkfs_options,
                        quota=fs_conf.has_quota(),
                        quota_options=fs_conf.get_quota_options())

            rc = self.fs_status_to_rc(status)
            if rc > result:
                result = rc

            if rc == RC_OK:
                if vlevel > 0:
                    print "Format successful."
            else:
                if rc == RC_RUNTIME_ERROR:
                    for nodes, msg in fs.proxy_errors:
                        print "%s: %s" % (nodes, msg)
                if vlevel > 0:
                    print "Format failed"

            # Call a post_format method if defined by the event handler.
            if hasattr(eh, 'post'):
                eh.post(fs)

        return result

