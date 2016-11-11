# Devices.py -- Device action classes
# Copyright (C) 2016 Stephane Thiell <sthiell@stanford.edu>
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
This module contains several classes to manage storage devices used as
Lustre target backend.
"""

from Shine.Lustre.Actions.Action import FSAction


class CommonDevice(FSAction):
    """
    Common class for StartDevice and StopDevice.
    """

    CHECK_MOUNTDATA = False

    def __init__(self, target, **kwargs):
        FSAction.__init__(self, target, **kwargs)
        self.dev_run_action = kwargs.get('dev_run_action')

class StartDevice(CommonDevice):
    """
    Start action for device.
    """

    NAME = 'start_device'
    CHECK_DEVICE = False

    def _prepare_cmd(self):
        # Replace variables - don't use basename() for device,
        # we want to pass he full path
        var_map = {'index': str(self.comp.index),
                   'dev'  : self.comp.dev}
        if self.comp.journal:
            var_map['jdev'] = self.comp.journal.dev

        cmd_cf = self.comp.dev_run_action.get_start_command()
        cmd = self._vars_substitute(cmd_cf, var_map)

        return [cmd]

class StopDevice(CommonDevice):
    """
    Stop action for device.
    """

    NAME = 'stop_device'
    CHECK_DEVICE = True

    def _prepare_cmd(self):
        # Replace variables - don't use basename() for device,
        # we want to pass he full path
        var_map = {'index': str(self.comp.index),
                   'dev'  : self.comp.dev}
        if self.comp.journal:
            var_map['jdev'] = self.comp.journal.dev

        cmd_cf = self.comp.dev_run_action.get_stop_command()
        cmd = self._vars_substitute(cmd_cf, var_map)

        return [cmd]
