# Fsck.py -- Check backend file system for each target
# Copyright (C) 2010 BULL S.A.S, CEA
# Copyright (C) 2012 CEA
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

import sys

from Shine.Commands.Status import Status

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

    ACTION = 'fsck'
    ACTIONING = 'checking'

    def __init__(self, verbose=1, fs_conf=None):
        FSGlobalEventHandler.__init__(self, verbose, fs_conf)
        self._comps = {}
        self._current = 0

    def handle_post(self, fs):
        if self.verbose > 0:
            Status.status_view_fs(fs, show_clients=False)

    def action_start(self, node, action, comp):
        self._comps[comp] = 0

    def action_progress(self, node, comp, result):
        self._comps[comp] = result.progress
        self._current = sum(self._comps.values()) / len(self._comps)
        header = self.ACTIONING.capitalize()
        sys.stdout.write("%s in progress: %d %%\r" % (header, self._current))
        sys.stdout.flush()
        if self._current == 100:
            sys.stdout.write("\n")


class LocalFsckEventHandler(FSLocalEventHandler):

    ACTION = 'fsck'
    ACTIONING = 'checking'

    def __init__(self, verbose=1):
        FSLocalEventHandler.__init__(self, verbose)
        self._comps = {}

    def action_start(self, node, action, comp):
        self._comps[comp] = 0

    def action_progress(self, node, comp, result):
        self._comps[comp] = result.progress
        current = sum(self._comps.values()) / len(self._comps)


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
        if not self.nodes_support.check_valid_list(fs.fs_name, servers,
                                                   "fsck"):
            return RC_FAILURE

        if not self.ask_confirm("Fsck %s on %s: are you sure?" % (fs.fs_name,
                                servers)):
            return RC_FAILURE

        # Call a pre_fsck method if defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)
        
        # Notify backend of file system status mofication
        fs_conf.set_status_fs_checking()

        # Fsck really.
        status = fs.fsck(addopts=self.addopts.get_options(),
                         failover=self.target_support.get_failover())

        rc = self.fs_status_to_rc(status)

        if rc == RC_OK:
            # Notify backend of file system status mofication
            fs_conf.set_status_fs_offline()

            if vlevel > 0:
                print "Fsck successful."
        else:
            # Notify backend of file system status mofication
            fs_conf.set_status_fs_critical()

            if rc == RC_RUNTIME_ERROR:
                for nodes, msg in fs.proxy_errors:
                    print "%s: %s" % (nodes, msg)
            if vlevel > 0:
                print "Fsck failed"

        # Call a post_fsck method if defined by the event handler.
        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
