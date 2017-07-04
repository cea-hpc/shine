# Execute.py -- Execute a custom command for any component.
# Copyright (C) 2012-2015 CEA
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
Shine `execute' command classes.

"""

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSLiveCommand, \
                                              CommandHelpException
from Shine.Commands.Base.CommandRCDefs import RC_OK, \
                                              RC_FAILURE, RC_TARGET_ERROR, \
                                              RC_CLIENT_ERROR, RC_RUNTIME_ERROR

# Lustre events and errors
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler, \
                                               FSLocalEventHandler
from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, EXTERNAL, OFFLINE, \
                                    TARGET_ERROR, CLIENT_ERROR, RUNTIME_ERROR, \
                                    MIGRATED


class Execute(FSLiveCommand):
    """
    shine execute [-f <fsname>] -o "..."
    """

    NAME = "execute"
    DESCRIPTION = "Execute a custom command"

    GLOBAL_EH = FSGlobalEventHandler
    LOCAL_EH = FSLocalEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_OK,
            MIGRATED : RC_OK,
            RECOVERING : RC_OK,
            EXTERNAL : RC_OK,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute(self):
        # Do not allow implicit filesystems format.
        if not self.options.additional:
            msg = "A custom command (-o) is required."
            raise CommandHelpException(msg, self)

        return FSLiveCommand.execute(self)

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        all_nodes = fs.components.managed().servers()
        if not self.check_valid_list(fs.fs_name, all_nodes, 'execute'):
            return RC_FAILURE

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        fs_result = fs.execute(failover=self.options.failover,
                               addopts=self.options.additional,
                               fanout=self.options.fanout,
                               dryrun=self.options.dryrun,
                               mountdata=self.options.mountdata)

        rc = self.fs_status_to_rc(fs_result)

        if rc == RC_OK:
            if vlevel > 0:
                print "Execute successful."

        elif rc == RC_RUNTIME_ERROR:
            self.display_proxy_errors(fs)
            print

        # Call a post_format method if defined by the event handler.
        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
