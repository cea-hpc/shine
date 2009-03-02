# Format.py -- Format file system targets
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

from Base.RemoteCommand import RemoteCommand
from Base.Support.Indexes import Indexes
from Base.Support.Nodes import Nodes
from Base.Support.FS import FS
from Base.Support.Target import Target
from Base.Support.Quiet import Quiet
from Base.Support.Verbose import Verbose
from RemoteCallEventHandler import RemoteCallEventHandler

from Shine.FSUtils import open_lustrefs

# timer events
import ClusterShell.Event

# lustre events
import Shine.Lustre.EventHandler

from ClusterShell.NodeSet import *
from ClusterShell.Task import task_self

import socket
import sys


class GlobalFormatEventHandler(Shine.Lustre.EventHandler.EventHandler,
        ClusterShell.Event.EventHandler):

    def __init__(self, verbose=1):
        self.verbose = verbose
        self.failures = 0
        self.success = 0
        self.nodeinfo = {}
        self.format_timer = None
        self.status_changed = True

    def ev_timer(self, timer):
        if len(self.nodeinfo) == 0:
            timer.invalidate()
            return

        if self.status_changed:
            self.status_changed = False
            print "Still waiting for %s ..." % \
                    NodeSet.fromlist(self.nodeinfo.iterkeys())

    def ev_format_journal_start(self, node, target):
        if self.verbose > 1:
            print "%s: Formatting %s %s journal (%s)" % (node, \
                    target.type.upper(), target.get_id(), target.jdev)

    def ev_format_journal_done(self, node, target):
        if self.verbose > 1:
            print "%s: Formatting of %s %s journal (%s) succeeded" % \
                    (node, target.type.upper(), target.get_id(), target.jdev)

    def ev_format_journal_failed(self, node, target, rc, message):
        self.failures += 1
        print "%s: Formatting of %s %s journal (%s) failed with error %d" % \
                (node, target.type.upper(), target.get_id(), target.jdev, rc)
        print message

    def ev_format_start(self, node, target, **kwargs):
        self.update_config_status(target, "formatting")

        self.status_changed = True

        v = self.nodeinfo.setdefault(node, 0)
        self.nodeinfo[node] = v + 1
        
        if self.verbose > 1:
            print "%s: Formatting %s %s (%s)" % (node, target.type.upper(), \
                    target.get_id(), target.dev)

        # start timer if first time called
        if self.verbose > 0 and not self.format_timer:
            task = task_self()
            self.format_timer = task.timer(2.0, handler=self, interval=10.0)
            assert self.format_timer is not None

    def ev_format_done(self, node, target):
        self.update_config_status(target, "succeeded")
        self.success += 1

        self.status_changed = True
        self.nodeinfo[node] -= 1
        if self.nodeinfo[node] == 0:
            del self.nodeinfo[node]

        if self.verbose > 1:
            print "%s: Formatting of %s %s (%s) succeeded" % \
                    (node, target.type.upper(), target.get_id(), target.dev)

    def ev_format_failed(self, node, target, rc, message):
        self.update_config_status(target, "failed")
        self.failures += 1

        self.status_changed = True
        self.nodeinfo[node] -= 1
        if self.nodeinfo[node] == 0:
            del self.nodeinfo[node]

        print "%s: Formatting of %s %s (%s) failed with error %d" % \
                (node, target.type.upper(), target.get_id(), target.dev, rc)
        print message

    def complete(self):
        if self.failures == 0:
            if self.verbose:
                print "Format successful."
            return 0
        else:
            print "Format failed (%d errors)" % self.failures
            return 1

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

    def ev_format_journal_start(self, node, target):
        print "Formatting %s %s journal (%s)" % (target.type.upper(), \
                target.get_id(), target.jdev)

    def ev_format_journal_done(self, node, target):
        print "Formatting of %s %s journal (%s) succeeded" % \
                (target.type.upper(), target.get_id(), target.jdev)

    def ev_format_journal_failed(self, node, target, rc, message):
        self.failures += 1
        print "Formatting of %s %s journal (%s) failed with error %d" % \
                (target.type.upper(), target.get_id(), target.jdev, rc)
        print message

    def ev_format_start(self, node, target):
        print "Formatting %s %s (%s)" % (target.type.upper(), \
                target.get_id(), target.dev)
        sys.stdout.flush()

    def ev_format_done(self, node, target):
        self.success += 1
        print "Formatting of %s %s (%s) succeeded" % \
                (target.type.upper(), target.get_id(), target.dev)

    def ev_format_failed(self, node, target, rc, message):
        self.failures += 1
        print "Formatting of %s %s (%s) failed with error %d" % \
                (target.type.upper(), target.get_id(), target.dev, rc)
        print message

    def complete(self):
        if self.failures == 0:
            print "Format successful."
            return 0
        else:
            print "Format failed (%d errors)" % self.failures
            return 1


class Format(RemoteCommand):
    """
    shine format -f <fsname> [-t <target>] [-i <index(es)>] [-n <nodes>]
    """
    
    def __init__(self):
        RemoteCommand.__init__(self)

        self.fs_support = FS(self, optional=False)
        self.target_support = Target(self)
        self.indexes_support = Indexes(self)
        self.nodes_support = Nodes(self)
        self.quiet_support = Quiet(self)
        self.verbose_support = Verbose(self)

    def get_name(self):
        return "format"

    def get_desc(self):
        return "Format file system targets."

    def execute(self):
        if not self.opt_f:
            raise "No FS"
        try:
            if self.local_flag or self.remote_call:
                self.opt_n = socket.gethostname()

            target = self.target_support.get_target()
            for fsname in self.fs_support.iter_fsname():
                vlevel = 1
                if self.verbose_support.has_verbose():
                    vlevel = 2
                elif self.quiet_support.has_quiet():
                    vlevel = 0

                # Select and install the appropriate event handler
                if self.remote_call:
                    handler = RemoteCallEventHandler()
                elif self.local_flag:

                    handler = LocalFormatEventHandler(vlevel)
                else:
                    handler = GlobalFormatEventHandler(vlevel)

                fs_conf, fs = open_lustrefs(fsname, target,
                        nodes=self.nodes_support.get_nodeset(),
                        indexes=self.indexes_support.get_rangeset(),
                        event_handler=handler)
                if not self.remote_call and not self.local_flag:
                    handler.set_fs_config(fs_conf)

                fs.set_debug(self.debug_support.has_debug())

                mkfs_options = {}
                format_params = {}
                for target_type in [ 'mgt', 'mdt', 'ost' ]:
                    format_params[target_type] = \
                            fs_conf.get_target_format_params(target_type)
                    mkfs_options[target_type] = \
                            fs_conf.get_target_mkfs_options(target_type) 

                fs.format(stripecount=fs_conf.get_stripecount(),
                          stripesize=fs_conf.get_stripesize(),
                          format_params=format_params,
                          mkfs_options=mkfs_options,
                          quota=fs_conf.has_quota(),
                          quota_options=fs_conf.get_quota_options())

                if not self.remote_call:
                    return handler.complete()

        except RangeSetParseError, e:
            print e
        except NodeSetParseRangeError, e:
            print e

        return 0

