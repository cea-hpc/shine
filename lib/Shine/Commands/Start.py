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
