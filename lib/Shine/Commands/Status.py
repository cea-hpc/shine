# Status.py -- Check remote filesystem servers and targets status
# Copyright (C) 2009 CEA
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
Shine `status' command classes.

The status command aims to return the real state of a Lustre filesystem
and its components, depending of the requested "view". Status views let
the Lustre administrator to either stand back and get a global status
of the filesystem, or if needed, to enquire about filesystem components
detailed states.
"""

# Configuration
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

# Command base class
from Base.FSLiveCommand import FSLiveCommand
from Base.CommandRCDefs import *
# Additional options
from Base.Support.View import View
# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler


# Error handling
from Exceptions import CommandBadParameterError

# Command helper
from Shine.FSUtils import open_lustrefs

# Command output formatting
from Shine.Utilities.AsciiTable import *

# Lustre events and errors
import Shine.Lustre.EventHandler
from Shine.Lustre.Disk import *
from Shine.Lustre.FileSystem import *

from ClusterShell.NodeSet import NodeSet

import os


(KILO, MEGA, GIGA, TERA) = (1024, 1048576, 1073741824, 1099511627776)


class GlobalStatusEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=1):
        self.verbose = verbose

    def ev_statustarget_start(self, node, target):
        pass

    def ev_statustarget_done(self, node, target):
        pass

    def ev_statustarget_failed(self, node, target, rc, message):
        print "%s: Failed to status %s %s (%s)" % (node, target.type.upper(), \
                target.get_id(), target.dev)
        print ">> %s" % message

    def ev_statusclient_start(self, node, client):
        pass

    def ev_statusclient_done(self, node, client):
        pass

    def ev_statusclient_failed(self, node, client, rc, message):
        print "%s: Failed to status of FS %s" % (node, client.fs.fs_name)
        print ">> %s" % message


class Status(FSLiveCommand):
    """
    shine status [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-qv]
    """

    def __init__(self):
        FSLiveCommand.__init__(self)
        self.view_support = View(self)

    def get_name(self):
        return "status"

    def get_desc(self):
        return "Check for file system target status."


    target_status_rc_map = { \
            MOUNTED : RC_ST_ONLINE,
            RECOVERING : RC_ST_RECOVERING,
            EXTERNAL : RC_ST_EXTERNAL,
            OFFLINE : RC_ST_OFFLINE,
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
            eh = self.install_eventhandler(None, GlobalStatusEventHandler(vlevel))

            fs_conf, fs = open_lustrefs(fsname, target,
                    nodes=self.nodes_support.get_nodeset(),
                    excluded=self.nodes_support.get_excludes(),
                    indexes=self.indexes_support.get_rangeset(),
                    labels=self.target_support.get_labels(),
                    event_handler=eh)

            # Warn if trying to act on wrong nodes
            all_nodes = fs.managed_target_servers() | fs.get_enabled_client_servers()
            if not self.nodes_support.check_valid_list(fsname, \
                    all_nodes, "check"):
                result = max(RC_FAILURE, result)
                continue

            fs.set_debug(self.debug_support.has_debug())

            status_flags = STATUS_ANY
            view = self.view_support.get_view()

            # default view
            if view is None:
                view = "fs"
            else:
                view = view.lower()

            # disable client checks when not requested
            if view.startswith("disk") or view.startswith("target"):
                status_flags &= ~STATUS_CLIENTS
            # disable servers checks when not requested
            if view.startswith("client"):
                status_flags &= ~(STATUS_SERVERS|STATUS_HASERVERS)

            fs_result = fs.status(status_flags)

            if fs_result == RUNTIME_ERROR:
                for nodes, msg in fs.proxy_errors:
                    print nodes
                    print '-' * 15
                    print msg
                print

            result = max(self.fs_status_to_rc(fs_result), result)

            if not self.remote_call and vlevel > 0:
                if view == "fs":
                    self.status_view_fs(fs)
                elif view.startswith("target"):
                    self.status_view_targets(fs)
                elif view.startswith("disk"):
                    self.status_view_disks(fs)
                else:
                    raise CommandBadParameterError(self.view_support.get_view(),
                            "fs, targets, disks")

        return result

    def status_view_targets(self, fs):
        """
        View: lustre targets
        """

        ldic = []
        group_key = lambda t: (t.DISPLAY_ORDER, t.index)
        for (order, index), enabled_targets in fs.enabled_targets(group_key=group_key):
            for target in enabled_targets:
                ldic.append(dict([["target", target.get_id()],
                    ["type", target.type.upper()],
                    ["nodes", NodeSet.fromlist(target.servers)],
                    ["device", target.dev],
                    ["index", target.index],
                    ["status", target.text_status()]]))

        layout = AsciiTableLayout()
        layout.set_show_header(True)
        layout.set_column("target", 0, AsciiTableLayout.LEFT, "target id",
                AsciiTableLayout.CENTER)
        layout.set_column("type", 1, AsciiTableLayout.LEFT, "type",
                AsciiTableLayout.CENTER)
        layout.set_column("index", 2, AsciiTableLayout.RIGHT, "idx",
                AsciiTableLayout.CENTER)
        layout.set_column("nodes", 3, AsciiTableLayout.LEFT, "nodes",
                AsciiTableLayout.CENTER)
        layout.set_column("device", 4, AsciiTableLayout.LEFT, "device",
                AsciiTableLayout.CENTER)
        layout.set_column("status", 5, AsciiTableLayout.LEFT, "status",
                AsciiTableLayout.CENTER)

        print "FILESYSTEM TARGETS (%s)" % fs.fs_name
        AsciiTable().print_from_list_of_dict(ldic, layout)


    def status_view_fs(cls, fs, show_clients=True):
        """
        View: lustre FS summary
        """

        ldic = []

        # Iterate over enabled TARGETS, grouped by display order and status
        key = lambda t: (t.DISPLAY_ORDER, t.text_status())
        for (disp, status), e_targets in fs.enabled_targets(group_key=key):
            targets = list(e_targets)
            ldic.append(dict([
                ["type", targets[0].type.upper()],
                ["count", len(targets)],
                ["nodes", NodeSet.fromlist([t.server for t in targets])],
                ["status", status]]))

        # If we want CLIENTS, iterate over enabled ones
        if show_clients:

            # XXX: As soon as Shine.Lustre.FileSystem supports grouping for Clients,
            # This could be simplified the same it is done for Targets.
            order = []
            states = {}
            for client in fs.enabled_clients():
                # Convert target.state to a human readable form.
                status = client.text_status()
                # Add to state mapping
                states.setdefault(("cli", status), NodeSet()).update(client.server)
                if ("cli", status) not in order:
                    order.append(("cli", status))

            # Read the state mapping we just build, using the recorded order.
            for (type, state) in order:
                ldic.append(dict([
                    ["type", str(type.upper())],
                    ["count", len(states[(type, state)])],
                    ["nodes", states[(type, state)]], 
                    ["status", state]]))

        layout = AsciiTableLayout()
        layout.set_show_header(True)
        layout.set_column("type", 0, AsciiTableLayout.CENTER, "type", AsciiTableLayout.CENTER)
        layout.set_column("count", 1, AsciiTableLayout.RIGHT, "#", AsciiTableLayout.CENTER)
        layout.set_column("nodes", 2, AsciiTableLayout.LEFT, "nodes", AsciiTableLayout.CENTER)
        layout.set_column("status", 3, AsciiTableLayout.LEFT, "status", AsciiTableLayout.CENTER)

        print "FILESYSTEM COMPONENTS STATUS (%s)" % fs.fs_name
        AsciiTable().print_from_list_of_dict(ldic, layout)

    status_view_fs = classmethod(status_view_fs)


    def status_view_disks(self, fs):
        """
        View: lustre disks
        """

        ldic = []
        jdev_col_enabled = False
        tag_col_enabled = False
        for type, e_targets in fs.managed_targets(group_attr="DISPLAY_ORDER"):
            for target in e_targets:

                if target.dev_size >= TERA:
                    dev_size = "%.1fT" % (target.dev_size/TERA)
                elif target.dev_size >= GIGA:
                    dev_size = "%.1fG" % (target.dev_size/GIGA)
                elif target.dev_size >= MEGA:
                    dev_size = "%.1fM" % (target.dev_size/MEGA)
                elif target.dev_size >= KILO:
                    dev_size = "%.1fK" % (target.dev_size/KILO)
                else:
                    dev_size = "%d" % target.dev_size

                if target.jdev:
                    jdev_col_enabled = True
                    jdev = target.jdev
                else:
                    jdev = ""

                if target.tag:
                    tag_col_enabled = True
                    tag = target.tag
                else:
                    tag = ""

                flags = []
                if target.has_need_index_flag():
                    flags.append("need_index")
                if target.has_first_time_flag():
                    flags.append("first_time")
                if target.has_update_flag():
                    flags.append("update")
                if target.has_rewrite_ldd_flag():
                    flags.append("rewrite_ldd")
                if target.has_writeconf_flag():
                    flags.append("writeconf")
                if target.has_upgrade14_flag():
                    flags.append("upgrade14")
                if target.has_param_flag():
                    flags.append("conf_param")

                ldic.append(dict([\
                    ["nodes", NodeSet.fromlist(target.servers)],
                    ["dev", target.dev],
                    ["size", dev_size],
                    ["jdev", jdev],
                    ["type", target.type.upper()],
                    ["index", target.index],
                    ["tag", tag],
                    ["label", target.label],
                    ["flags", ' '.join(flags)],
                    ["fsname", target.fs.fs_name],
                    ["status", target.text_status()]]))

        layout = AsciiTableLayout()
        layout.set_show_header(True)
        i = 0
        layout.set_column("dev", i, AsciiTableLayout.LEFT, "device",
                AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("nodes", i, AsciiTableLayout.LEFT, "node(s)",
                AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("size", i, AsciiTableLayout.RIGHT, "dev size",
                AsciiTableLayout.CENTER)
        if jdev_col_enabled:
            i += 1
            layout.set_column("jdev", i, AsciiTableLayout.RIGHT, "journal device",
                    AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("type", i, AsciiTableLayout.LEFT, "type",
                AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("index", i, AsciiTableLayout.RIGHT, "index",
                AsciiTableLayout.CENTER)
        if tag_col_enabled:
            i += 1
            layout.set_column("tag", i, AsciiTableLayout.LEFT, "tag",
                    AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("label", i, AsciiTableLayout.LEFT, "label",
                AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("flags", i, AsciiTableLayout.LEFT, "ldd flags",
                AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("fsname", i, AsciiTableLayout.LEFT, "fsname",
                AsciiTableLayout.CENTER)
        i += 1
        layout.set_column("status", i, AsciiTableLayout.LEFT, "status",
                AsciiTableLayout.CENTER)

        print "FILESYSTEM DISKS (%s)" % fs.fs_name
        AsciiTable().print_from_list_of_dict(ldic, layout)

