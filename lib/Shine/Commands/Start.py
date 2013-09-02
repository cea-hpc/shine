# Start.py -- Start file system
# Copyright (C) 2007-2013 CEA
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

"""
Shine `start' command classes.

The start command aims to start Lustre filesystem servers or just some
of the filesystem targets on local or remote servers. It is available
for any filesystems previously installed and formatted.
"""

from Shine.CLI.Display import display
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
            print display(self.command, fs, supports='start')

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

        # Warn if trying to act on wrong nodes
        comps = fs.components.managed(supports='start')
        if not self.check_valid_list(fs.fs_name, comps.servers(), 'start'):
            return RC_FAILURE

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)
            
        status = fs.start(mount_options=mount_options,
                          mount_paths=mount_paths,
                          addopts=self.options.additional,
                          failover=self.options.failover,
                          mountdata=self.options.mountdata)

        rc = self.fs_status_to_rc(status)

        if rc == RC_OK:
            if vlevel > 0:
                print "Start successful."
            tuning = Tune.get_tuning(fs_conf)
            status = fs.tune(tuning, comps=comps)
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

        return rc
