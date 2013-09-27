# Mount.py -- Mount file system on clients
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
Shine `mount' command classes.

The mount command aims to start Lustre filesystem clients.
"""

# Command helper
from Shine.Commands.Tune import Tune

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

class Mount(FSLiveCommand):
    """
    shine mount
    """

    NAME = "mount"
    DESCRIPTION = "Mount file system clients."

    GLOBAL_EH = FSGlobalEventHandler
    LOCAL_EH = FSLocalEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_OK,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_FAILURE,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        comps = fs.components.managed(supports='mount')
        if not self.check_valid_list(fs.fs_name, comps.servers(), "mount"):
            return RC_FAILURE

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        status = fs.mount(addopts=self.options.additional)

        rc = self.fs_status_to_rc(status)

        if not self.options.remote:
            if rc == RC_OK:
                if vlevel > 0:
                    key = lambda c: c.state == MOUNTED
                    print "%s was successfully mounted on %s" % \
                        (fs.fs_name, comps.filter(key=key).servers())

                # Apply tuning after successful mount(s)
                tuning = Tune.get_tuning(fs_conf)
                status = fs.tune(tuning, comps=comps)
                if status == MOUNTED:
                    print "Filesystem tuning applied on %s" % comps.servers()
                elif status == RUNTIME_ERROR:
                    rc = RC_RUNTIME_ERROR
                    self.display_proxy_errors(fs)

            else:
                # Display a failure message in case of previous failed
                # mounts. For now, if one mount fail, the tuning is
                # skipped. Use `shine tune' to manually tune the FS.
                # Trac ticket #46 aims to improve this.
                if vlevel > 0:
                    print "Tuning skipped!"
                if rc == RC_RUNTIME_ERROR:
                    self.display_proxy_errors(fs)

        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
