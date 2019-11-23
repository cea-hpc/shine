# StopTarget.py -- Lustre action class: stop (umount) target
# Copyright (C) 2009-2012 CEA
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
Action class to stop Lustre target.
"""

from ClusterShell.Task import task_self

from Shine.Lustre.Actions.Action import FSAction, Result

class StopTarget(FSAction):
    """
    File system target start action class.
    """

    NAME = 'stop'

    def _already_done(self):
        """Return a Result object is the target is already unmounted."""
        if self.comp.is_stopped():
            return Result(message="%s is already stopped" % self.comp.label)

        # LBUG #18624
        if not self.comp.dev_isblk:
            task_self().set_info("fanout", 1)

        return None

    def _prepare_cmd(self):
        """
        Unmount file system target.
        """

        command = ["umount"]

        # Also free the loop device if needed
        if not self.comp.dev_isblk:
            command.append("-d")

        # Process additional umount options
        if self.addopts:
            command.append(self.addopts)

        command.append(self.comp.mntdev)

        return command
