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

from Shine.Commands.Status import Status

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSTargetLiveCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_ST_EXTERNAL, \
                                              RC_FAILURE, RC_TARGET_ERROR, \
                                              RC_CLIENT_ERROR, RC_RUNTIME_ERROR
# Lustre events
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler, \
                                               FSLocalEventHandler

from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, EXTERNAL, OFFLINE, \
                                    TARGET_ERROR, CLIENT_ERROR, RUNTIME_ERROR

class GlobalStopEventHandler(FSGlobalEventHandler):

    ACTION = 'stop'
    ACTIONING = 'stopping'

    def handle_post(self, fs):
        if self.verbose > 0:
            Status.status_view_fs(fs, show_clients=False)

    def ev_stoptarget_start(self, node, comp):
        self.update_config_status(comp, "stopping")
        self.action_start(node, comp)

    def ev_stoptarget_done(self, node, comp):
        self.update_config_status(comp, "done")
        self.action_done(node, comp)

    def ev_stoptarget_failed(self, node, comp, rc, message):
        self.update_config_status(comp, "failed")
        self.action_failed(node, comp, rc, message)

    def ev_stoprouter_start(self, node, comp):
        self.action_start(node, comp)

    def ev_stoprouter_done(self, node, comp):
        self.action_done(node, comp)

    def ev_stoprouter_failed(self, node, comp, rc, message):
        self.action_failed(node, comp, rc, message)

    def update_config_status(self, target, status):
        # Retrieve the right target from the configuration
        target_list = [self.fs_conf.get_target_from_tag_and_type(target.tag,
            target.TYPE.upper())]

        # Change the status of targets to register their running state
        if status == "done":
            self.fs_conf.set_status_targets_offline(target_list, None)
        elif status == "failed":
            self.fs_conf.set_status_targets_unreachable(target_list, None)
        else:
            self.fs_conf.set_status_targets_stopping(target_list, None)

class LocalStopEventHandler(FSLocalEventHandler):

    def ev_stoptarget_start(self, node, comp):
        self.action_start(node, comp)

    def ev_stoptarget_done(self, node, comp):
        self.action_done(node, comp)

    def ev_stoptarget_failed(self, node, comp, rc, message):
        self.action_failed(node, comp, rc, message)

    def ev_stoprouter_start(self, node, comp):
        self.action_start(node, comp)

    def ev_stoprouter_done(self, node, comp):
        self.action_done(node, comp)

    def ev_stoprouter_failed(self, node, comp, rc, message):
        self.action_failed(node, comp, rc, message)


class Stop(FSTargetLiveCommand):
    """
    shine stop [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-qv]
    """

    NAME = "stop"
    DESCRIPTION = "Stop file system servers."

    GLOBAL_EH = GlobalStopEventHandler
    LOCAL_EH = LocalStopEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_FAILURE,
            RECOVERING : RC_FAILURE,
            EXTERNAL : RC_ST_EXTERNAL,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute_fs(self, fs, fs_conf, eh, vlevel):
    
        # Prepare options...
        mount_options = {}
        mount_paths = {}
        for target_type in [ 'mgt', 'mdt', 'ost' ]:
            mount_options[target_type] = fs_conf.get_target_mount_options(target_type)
            mount_paths[target_type] = fs_conf.get_target_mount_path(target_type)

        # Ignore all clients for this command
        fs.disable_clients()

        # Warn if trying to act on wrong nodes
        if not self.nodes_support.check_valid_list(fs.fs_name, \
                fs.managed_component_servers(supports='stop'), "stop"):
            return RC_FAILURE

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)
            
        # Notify backend of file system status mofication
        fs_conf.set_status_fs_stopping()

        status = fs.stop(addopts=self.addopts.get_options(),
                         failover=self.target_support.get_failover())

        rc = self.fs_status_to_rc(status)

        if rc == RC_OK:
            # Notify backend of file system status mofication
            fs_conf.set_status_fs_offline()

            if vlevel > 0:
                print "Stop successful."
        elif rc == RC_RUNTIME_ERROR:
            # Notify backend of file system status mofication
            fs_conf.set_status_fs_offline_failed()

            for nodes, msg in fs.proxy_errors:
                print "%s: %s" % (nodes, msg)

        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
