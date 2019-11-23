# StopClient.py -- Umount client
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
Action class to stop Lustre client.
"""

from Shine.Lustre.Actions.Action import FSAction, Result

class StopClient(FSAction):
    """
    File system client stop (ie. umount) action class.
    """

    NAME = 'umount'

    def _already_done(self):
        """Return a Result object if the filesystem is not mounted already."""
        if self.comp.is_stopped():
            return Result("%s is not mounted" % self.comp.fs.fs_name)
        else:
            return None

    def _prepare_cmd(self):
        """
        Unmount file system client.
        """
        command = ["umount"]

        # Process additional option for umount command
        if self.addopts:
            command.append(self.addopts)

        mount_path = self._vars_substitute(self.comp.mount_path)
        command.append(mount_path)

        return command
