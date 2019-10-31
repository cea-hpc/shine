# Modules.py -- Load/Unload Lustre modules
# Copyright (C) 2013-2015 CEA
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

import os

"""
Action classes for Lustre module managements.
"""

from Shine.Configuration.Globals import Globals

from Shine.Lustre import ServerError
from Shine.Lustre.Actions.Action import CommonAction, ACT_OK, ACT_ERROR, \
                                        Result, ErrorResult, Action, ActionInfo

class ServerAction(CommonAction):
    """
    Base class for any server-specific Action.

    At minimum, _shell() method should be overloaded.
    """

    def __init__(self, srv, **kwargs):
        CommonAction.__init__(self)
        self.dryrun = kwargs.get('dryrun', False)
        self.server = srv

    def info(self):
        """Return a ActionInfo describing this action."""
        return ActionInfo(self, self.server)

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
        self.server.action_event(self, 'start')
        try:
            self.server.lustre_check()

            result = self._already_done()
            if not result:
                self._shell()
            else:
                self.server.action_event(self, 'done', result)
                self.set_status(ACT_OK)

        except ServerError as error:
            self.server.action_event(self, 'failed', Result(str(error)))
            self.set_status(ACT_ERROR)

    def _prepare_cmd(self):
        """
        Return an array of command and arguments to be run by launch() method.
        """
        raise NotImplementedError

    def _shell(self):
        """Create a command line and schedule it to be run by self.task"""
        # Call specific method to prepare command line
        command = self._prepare_cmd()

        # Extent path if defined
        path = Globals().get('command_path')
        if path:
            command.insert(0, "export PATH=%s:${PATH};" % path)

        # Add the command to be scheduled
        cmdline = ' '.join(command)

        self.server.hdlr.log('detail', msg='[RUN] %s' % cmdline)

        if self.dryrun:
            self.server.action_event(self, 'done')
            self.set_status(ACT_OK)
        else:
            self.task.shell(cmdline, handler=self)

    def ev_close(self, worker):
        """
        Check process termination status and set action status.
        """
        Action.ev_close(self, worker)

        self.server.lustre_check()

        # Action timed out
        if worker.did_timeout():
            self.server.action_event(self, 'timeout')
            self.set_status(ACT_ERROR)

        # Action succeeded
        elif worker.retcode() == 0:
            result = Result(duration=self.duration, retcode=worker.retcode())
            self.server.action_event(self, 'done', result)
            self.set_status(ACT_OK)

        # Action failed
        else:
            result = ErrorResult(worker.read(), self.duration, worker.retcode())
            self.server.action_event(self, 'failed', result)
            self.set_status(ACT_ERROR)

class LoadModules(ServerAction):
    """
    Load some lustre modules using modprobe.

    By default, it is 'lustre', use `modname' if you want to load another one.
    """

    NAME = 'load modules'

    def __init__(self, srv, modname='lustre', options=None, **kwargs):
        ServerAction.__init__(self, srv, **kwargs)
        self._modname = modname
        self._options = options

    def info(self):
        """Return a ActionInfo describing this action."""
        return ActionInfo(self, self.server,
                          "load module '%s'" % self._modname)

    def _already_done(self):
        if self._modname in self.server.modules:
            return Result("'%s' is already loaded" % self._modname)

    def _prepare_cmd(self):
        command = ['modprobe %s' % self._modname]
        if self._options is not None:
            command.append(' "%s"' % self._options)
        return command


class UnloadModules(ServerAction):
    """
    Unload all lustre modules using 'lustre_rmmod'
    """

    NAME = 'unload modules'

    def _device_count(self):
        """Return the number of loaded Lustre devices."""
        count = 0
        try:
            devicesfile = '/sys/kernel/debug/lustre/devices'
            # Compat code for lustre versions prior to 2.10 (2.9 and below)
            if os.access('/proc/fs/lustre/devices', os.F_OK):
                devicesfile = '/proc/fs/lustre/devices'

            devices = open(devicesfile)

            for line in devices.readlines():

                # Workaround for racy Lustre behaviour.
                # When unmounting, some lustre devs could be a little bit slow
                # to be cleared, ignore it as module unloading will probably be
                # ok.
                _, state, _, _, _, refcnt = line.split()
                if state == 'ST' and refcnt == '0':
                    continue

                count += 1

            devices.close()
        except IOError:
            pass

        return count

    def _already_done(self):
        if len(self.server.modules) == 0:
            return Result("modules already unloaded")

        # If some devices are still loaded, do not try to unload
        # and do not consider this as an error.
        count = self._device_count()
        if count > 0:
            return Result('ignoring, still %d in-use lustre device(s)' % count)

        # Check still in use?
        self.server.raise_if_mod_in_use()

    def _prepare_cmd(self):
        return ['lustre_rmmod']
