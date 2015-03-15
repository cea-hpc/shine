# Start.py -- Start file system
# Copyright (C) 2007-2015 CEA
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


class Start(FSTargetLiveCommand):
    """
    shine start [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-qv]
    """

    NAME = "start"
    DESCRIPTION = "Start file system servers."

    GLOBAL_EH = FSGlobalEventHandler
    LOCAL_EH = FSLocalEventHandler

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
        for tgt_type in [ 'mgt', 'mdt', 'ost' ]:
            mount_options[tgt_type] = fs_conf.get_target_mount_options(tgt_type)
            mount_paths[tgt_type] = fs_conf.get_target_mount_path(tgt_type)

        # Warn if trying to act on wrong nodes
        comps = fs.components.managed(supports='start')
        if not self.check_valid_list(fs.fs_name, comps.servers(), 'start'):
            return RC_FAILURE

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        self.copy_tuning(fs, comps=comps)

        status = fs.start(mount_options=mount_options,
                          mount_paths=mount_paths,
                          addopts=self.options.additional,
                          failover=self.options.failover,
                          fanout=self.options.fanout,
                          dryrun=self.options.dryrun,
                          mountdata=self.options.mountdata,
                          tunings=Tune.get_tuning(fs_conf, fs.components))

        rc = self.fs_status_to_rc(status)

        if rc == RC_OK:
            if vlevel > 0:
                print "Start successful."
        elif rc == RC_RUNTIME_ERROR:
            self.display_proxy_errors(fs)

        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
