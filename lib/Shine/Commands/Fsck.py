# Fsck.py -- Check backend file system for each target
# Copyright (C) 2010 BULL S.A.S, CEA
# Copyright (C) 2012-2013 CEA
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
Shine `fsck' command.
Run a low-level filesystem check for filesystem targets.
"""

import sys

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSTargetLiveCriticalCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_ST_EXTERNAL, \
                                              RC_FAILURE, RC_TARGET_ERROR, \
                                              RC_CLIENT_ERROR, RC_RUNTIME_ERROR
# Lustre events
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler, \
                                               FSLocalEventHandler

from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, EXTERNAL, OFFLINE, \
                                    TARGET_ERROR, CLIENT_ERROR, RUNTIME_ERROR

class GlobalFsckEventHandler(FSGlobalEventHandler):
    """Display a global progress status for all components."""

    def __init__(self, command):
        FSGlobalEventHandler.__init__(self, command)
        self._comps = {}
        self._current = 0

    def action_start(self, node, action, comp):
        self._comps[comp] = 0

    def action_progress(self, node, action, comp, result):
        self._comps[comp] = result.progress
        self._current = sum(self._comps.values()) / len(self._comps)
        header = self.command.NAME.capitalize()
        sys.stdout.write("%s in progress: %d %%\r" % (header, self._current))
        sys.stdout.flush()
        if self._current == 100:
            sys.stdout.write("\n")


class LocalFsckEventHandler(FSLocalEventHandler):
    """Display a global progress status for all components."""

    def __init__(self, command):
        FSLocalEventHandler.__init__(self, command)
        self._comps = {}
        self._current = 0

    def action_start(self, node, action, comp):
        self._comps[comp] = 0

    def action_progress(self, node, action, comp, result):
        self._comps[comp] = result.progress
        self._current = sum(self._comps.values()) / len(self._comps)
        header = self.command.NAME.capitalize()
        sys.stdout.write("%s in progress: %d %%\r" % (header, self._current))
        sys.stdout.flush()
        if self._current == 100:
            sys.stdout.write("\n")


class Fsck(FSTargetLiveCriticalCommand):
    """
    shine fsck -f <fsname> [-t <target>] [-i <index(es)>] [-n <nodes>]
    """
    
    NAME = "fsck"
    DESCRIPTION = "Fsck on targets backend file system."

    GLOBAL_EH = GlobalFsckEventHandler
    LOCAL_EH = LocalFsckEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_FAILURE,
            EXTERNAL : RC_ST_EXTERNAL,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        servers = fs.components.managed(supports='fsck').servers()
        if not self.check_valid_list(fs.fs_name, servers, "fsck"):
            return RC_FAILURE

        if not self.ask_confirm("Fsck %s on %s: are you sure?" % (fs.fs_name,
                                servers)):
            return RC_FAILURE

        # Call a pre_fsck method if defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)
        
        # Fsck really.
        status = fs.fsck(addopts=self.options.additional,
                         failover=self.options.failover,
                         mountdata=self.options.mountdata)

        rc = self.fs_status_to_rc(status)

        if rc == RC_OK:
            if vlevel > 0:
                print "Fsck successful."
        else:
            if rc == RC_RUNTIME_ERROR:
                self.display_proxy_errors(fs)
            if vlevel > 0:
                print "Fsck failed"

        # Call a post_fsck method if defined by the event handler.
        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
