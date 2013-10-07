# Modules.py -- Load/Unload Lustre modules
# Copyright (C) 2013 CEA
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
Action classes for Lustre module managements.
"""

from Shine.Lustre import ServerError
from Shine.Lustre.Actions.Action import CommonAction, ACT_OK, ACT_ERROR

class ServerAction(CommonAction):
    """
    Base class for any server-specific Action.

    At minimum, _shell() method should be overloaded.
    """

    def __init__(self, srv):
        CommonAction.__init__(self)
        self.server = srv

    def _already_done(self):
        """
        Verify if the action work is already done.

        Return a Result object if done, None otherwise.
        """
        return False

    def _launch(self):
        """
        Run the command to process the action.

        It checks the command could be really be run before running it.
        """
        try:
            self.server.lustre_check()

            result = self._already_done()
            if not result:
                self._shell()
            else:
                self.set_status(ACT_OK)

        except ServerError:
            self.set_status(ACT_ERROR)

    def _shell(self):
        """Create a command line and schedule it to be run by self.task"""
        raise NotImplementedError

    def ev_close(self, worker):
        """
        Check process termination status and set action status.
        """
        CommonAction.ev_close(self, worker)

        self.server.lustre_check()

        # Action timed out
        if worker.did_timeout():
            self.set_status(ACT_ERROR)

        # Action succeeded
        elif worker.retcode() == 0:
            self.set_status(ACT_OK)

        # Action failed
        else:
            self.set_status(ACT_ERROR)

class LoadModules(ServerAction):
    """
    Load some lustre modules using modprobe.

    By default, it is 'lustre', use `modname' if you want to load another one.
    """

    NAME = 'loadmodules'

    def __init__(self, srv, modname='lustre', options=None):
        ServerAction.__init__(self, srv)
        self._modname = modname
        self._options = options

    def _already_done(self):
        if 'lustre' in self.server.modules:
            return True

    def _shell(self):
        command = "modprobe %s" % self._modname
        if self._options is not None:
            command += ' "%s"' % self._options
        self.task.shell(command, handler=self)


class UnloadModules(ServerAction):
    """
    Unload all lustre modules using 'lustre_rmmod'
    """

    NAME = 'unloadmodules'

    def _device_count(self):
        """Return the number of loaded Lustre devices."""
        count = 0
        try:
            devices = open('/proc/fs/lustre/devices')
            for line in devices:
                count += 1
            devices.close()
        except IOError:
            pass

        return count

    def _already_done(self):
        if len(self.server.modules) == 0:
            return True

        # If some devices are still loaded, do not try to unload
        # and do not consider this as an error.
        if self._device_count() > 0:
            return True

        # Check still in use?
        self.server.raise_if_mod_in_use()

    def _shell(self):
        command = 'lustre_rmmod'
        self.task.shell(command, handler=self)
