# Umount.py -- Unmount file system on clients
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
Shine `umount' command classes.

The umount command aims to stop Lustre filesystem clients.
"""

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSLiveCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, \
                                              RC_FAILURE, RC_TARGET_ERROR, \
                                              RC_CLIENT_ERROR, RC_RUNTIME_ERROR
# Lustre events
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler, \
                                               FSLocalEventHandler

from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, OFFLINE, \
                                    TARGET_ERROR, CLIENT_ERROR, RUNTIME_ERROR


class Umount(FSLiveCommand):
    """
    shine umount
    """

    NAME = "umount"
    DESCRIPTION = "Unmount file system clients."

    GLOBAL_EH = FSGlobalEventHandler
    LOCAL_EH = FSLocalEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_FAILURE,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        comps = fs.components.managed(supports='umount')
        if not self.check_valid_list(fs.fs_name, comps.servers(), "unmount"):
            return RC_FAILURE

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        status = fs.umount(addopts=self.options.additional,
                           dryrun=self.options.dryrun,
                           fanout=self.options.fanout,
                           need_unload=self.options.need_unload)

        rc = self.fs_status_to_rc(status)

        if not self.options.remote:
            if rc == RC_OK:
                if vlevel > 0:
                    key = lambda c: c.state == OFFLINE
                    print "%s was successfully unmounted on %s" % \
                        (fs.fs_name, comps.filter(key=key).servers())
            elif rc == RC_RUNTIME_ERROR:
                self.display_proxy_errors(fs)

        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
