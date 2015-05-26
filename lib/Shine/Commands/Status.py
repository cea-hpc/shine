# Status.py -- Check remote filesystem servers and targets status
# Copyright (C) 2009-2013 CEA
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
Shine `status' command classes.

The status command aims to return the real state of a Lustre filesystem
and its components, depending of the requested "view". Status views let
the Lustre administrator to either stand back and get a global status
of the filesystem, or if needed, to enquire about filesystem components
detailed states.
"""

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSTargetLiveCommand
from Shine.Commands.Base.CommandRCDefs import RC_ST_OFFLINE, RC_ST_EXTERNAL, \
                                              RC_ST_ONLINE, RC_ST_RECOVERING, \
                                              RC_FAILURE, RC_TARGET_ERROR, \
                                              RC_CLIENT_ERROR, RC_RUNTIME_ERROR

# Lustre events and errors
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler, \
                                               FSLocalEventHandler
from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, EXTERNAL, OFFLINE, \
                                    TARGET_ERROR, CLIENT_ERROR, RUNTIME_ERROR, \
                                    MIGRATED


class Status(FSTargetLiveCommand):
    """
    shine status [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-qv]
    """

    NAME = "status"
    DESCRIPTION = "Check for file system target status."

    GLOBAL_EH = FSGlobalEventHandler
    LOCAL_EH = FSLocalEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_ST_ONLINE,
            MIGRATED : RC_ST_ONLINE,
            RECOVERING : RC_ST_RECOVERING,
            EXTERNAL : RC_ST_EXTERNAL,
            OFFLINE : RC_ST_OFFLINE,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        all_nodes = fs.components.managed().servers()
        if not self.check_valid_list(fs.fs_name, all_nodes, "check"):
            return RC_FAILURE

        # Apply 'status' only to required components
        comps = fs.components
        if self.options.view.startswith("target"):
            comps = comps.filter(supports='index')
        if self.options.view.startswith("disk"):
            comps = comps.filter(supports='dev')

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        fs_result = fs.status(comps,
                              failover=self.options.failover,
                              dryrun=self.options.dryrun,
                              fanout=self.options.fanout)

        if fs_result == RUNTIME_ERROR:
            self.display_proxy_errors(fs)
            print

        result = self.fs_status_to_rc(fs_result)

        # Call a handle_post() method if defined by the event handler.
        if hasattr(eh, 'post'):
            eh.post(fs)

        return result
