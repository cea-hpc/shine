# Tunefs.py -- Tune file system targets
# Copyright (C) 2011-2013 CEA
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
Shine `tunefs' command classes.

The tunefs command aims to modify target on-disk parameter without reformating
it.
"""

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSLiveCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_ST_EXTERNAL, \
                                              RC_FAILURE, RC_TARGET_ERROR, \
                                              RC_CLIENT_ERROR, RC_RUNTIME_ERROR
# Lustre events
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler, \
                                               FSLocalEventHandler

from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, EXTERNAL, OFFLINE, \
                                    TARGET_ERROR, CLIENT_ERROR, RUNTIME_ERROR, \
                                    MIGRATED


class Tunefs(FSLiveCommand):
    """
    shine tunefs -f <fsname> [...]
    """

    NAME = "tunefs"
    DESCRIPTION = "Tune file system targets."

    CRITICAL = True

    GLOBAL_EH = FSGlobalEventHandler
    LOCAL_EH = FSLocalEventHandler

    TARGET_STATUS_RC_MAP = { \
            MOUNTED : RC_FAILURE,
            MIGRATED : RC_FAILURE,
            EXTERNAL : RC_ST_EXTERNAL,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        servers = fs.components.managed(supports='tunefs').servers()
        if not self.check_valid_list(fs.fs_name, servers, "tunefs"):
            return RC_FAILURE

        if not self.ask_confirm("Tunefs %s on %s: are you sure?" % (fs.fs_name,
                                                                    servers)):
            return RC_FAILURE

        format_params = {}
        for target_type in [ 'mgt', 'mdt', 'ost' ]:
            format_params[target_type] = \
                    fs_conf.get_target_format_params(target_type)

        # Call a pre_format method if defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        # Format really.
        status = fs.tunefs(stripecount=fs_conf.get_stripecount(),
                    stripesize=fs_conf.get_stripesize(),
                    format_params=format_params,
                    quota=fs_conf.has_quota(),
                    quota_type=fs_conf.get_quota_type(),
                    addopts=self.options.additional,
                    fanout=self.options.fanout,
                    dryrun=self.options.dryrun,
                    failover=self.options.failover,
                    writeconf=True,
                    mountdata=self.options.mountdata)

        rc = self.fs_status_to_rc(status)

        if rc == RC_OK:
            if vlevel > 0:
                print "Tunefs successful."
        else:
            if rc == RC_RUNTIME_ERROR:
                self.display_proxy_errors(fs)
            if vlevel > 0:
                print "Tunefs failed"

        # Call a post_tunefs method if defined by the event handler.
        if hasattr(eh, 'post'):
            eh.post(fs)

        return rc
