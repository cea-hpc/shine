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

from Shine.Commands.Status import Status
from Shine.Commands.Tune import Tune

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

class GlobalStartEventHandler(FSGlobalEventHandler):

    ACTION = 'start'
    ACTIONING = 'starting'

    def handle_post(self, fs):
        if self.verbose > 0:
            Status.status_view_fs(fs, show_clients=False)

    def action_start(self, node, comp):
        self.update_config_status(comp, "start")
        FSGlobalEventHandler.action_start(self, node, comp)

    def action_done(self, node, comp):
        self.update_config_status(comp, "done")
        FSGlobalEventHandler.action_done(self, node, comp)

    def action_failed(self, node, comp, result):
        self.update_config_status(comp, "failed")
        FSGlobalEventHandler.action_failed(self, node, comp, result)

    def update_config_status(self, target, status):
        # Router is not managed in DB
        if target.TYPE == 'router':
            return

        # Retrieve the right target from the configuration
        target_list = [self.fs_conf.get_target_from_tag_and_type(target.tag,
            target.TYPE.upper())]

        # Change the status of targets to register their running state
        if status == "done":
            self.fs_conf.set_status_targets_online(target_list, None)
        elif status == "failed":
            self.fs_conf.set_status_targets_offline(target_list, None)
        else:
            self.fs_conf.set_status_targets_starting(target_list, None)

class LocalStartEventHandler(FSLocalEventHandler):

    ACTION = 'start'
    ACTIONING = 'starting'


class Start(FSTargetLiveCommand):
    """
    shine start [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-qv]
    """

    NAME = "start"
    DESCRIPTION = "Start file system servers."

    GLOBAL_EH = GlobalStartEventHandler
    LOCAL_EH = LocalStartEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_OK,
            RECOVERING : RC_OK,
            EXTERNAL : RC_ST_EXTERNAL,
            OFFLINE : RC_FAILURE,
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
        servers = fs.components.managed(supports='start').servers()
        if not self.nodes_support.check_valid_list(fs.fs_name, servers,
                                                   'start'):
            return RC_FAILURE

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

        return rc
