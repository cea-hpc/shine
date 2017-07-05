# FSLiveCommand.py -- Base commands class : live filesystem
# Copyright (C) 2009-2015 CEA
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
Base class for live filesystem commands (start, stop, status, etc.).
"""

from Shine.Configuration.Globals import Globals

from Shine.Commands.Base.Command import RemoteCommand, CommandHelpException

# Command helper
from Shine.FSUtils import open_lustrefs

# Error handling
from Shine.Commands.Base.CommandRCDefs import RC_RUNTIME_ERROR

class FSLiveCommand(RemoteCommand):
    """
    shine <cmd> [-f <fsname>] [-n <nodes>] [-dqv]

    'CRITICAL' could be set if command will run action that can
    damage filesystems.
    """

    GLOBAL_EH = None
    LOCAL_EH = None

    CRITICAL = False

    TARGET_STATUS_RC_MAP = {}

    def fs_status_to_rc(self, status_set):
        mapped_status = [self.TARGET_STATUS_RC_MAP.get(st, RC_RUNTIME_ERROR) for st in status_set]
        return max(mapped_status)

    def _open_fs(self, fsname, eh):
        return open_lustrefs(fsname,
                             self.options.targets,
                             nodes=self.options.nodes,
                             excluded=self.options.excludes,
                             failover=self.options.failover,
                             indexes=self.options.indexes,
                             labels=self.options.labels,
                             event_handler=eh)

    def execute_fs(self, fs, fs_conf, eh, vlevel):
        raise NotImplemented("Derived class must implement.")

    def execute(self):
        first = True

        # Option sanity check
        self.forbidden(self.options.model, "-m, use -f")

        # Do not allow implicit filesystems format.
        if self.CRITICAL and not self.options.fsnames:
            msg = "A filesystem is required (use -f)."
            raise CommandHelpException(msg, self)

        result = 0

        self.init_execute()

        # Install appropriate event handler.
        local_eh = None
        global_eh = None
        if self.LOCAL_EH:
            local_eh = self.LOCAL_EH(self)
        if self.GLOBAL_EH:
            global_eh = self.GLOBAL_EH(self)
        eh = self.install_eventhandler(local_eh, global_eh)

        for fsname in self.iter_fsname():

            # Open configuration and instantiate a Lustre FS.
            fs_conf, fs = self._open_fs(fsname, eh)

            # Define debuggin level
            fs.set_debug(self.options.debug)

            # Separate each fsname with a blank line
            if not first:
                print
            first = False

            # Run the real job
            vlevel = self.options.verbose
            result = max(result, self.execute_fs(fs, fs_conf, eh, vlevel))

        return result
