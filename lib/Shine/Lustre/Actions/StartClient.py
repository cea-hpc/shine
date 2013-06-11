# StartClient.py -- Mount client
# Copyright (C) 2009-2013 CEA
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
This module contains the FSAction class for mounting a Lustre filesystem, from
a client side.
"""

from Shine.Lustre.Actions.Action import FSAction, Result

class StartClient(FSAction):
    """
    File system client start (ie. mount) action class.
    """

    NAME = 'mount'

    def _already_done(self):
        """Return a Result object if the client is already mounted."""
        if self.comp.is_started():
            return Result("%s is already mounted on %s" %
                          (self.comp.fs.fs_name, self.comp.mtpt))
        else:
            return None

    def _prepare_cmd(self):
        """
        Prepare client file system mount command line.
        """

        mount_path = self._vars_substitute(self.comp.mount_path)

        command = ["mkdir -p \"%s\"" % mount_path]
        command += ["&& /bin/mount -t lustre"]

        options = []

        # Mount options from configuration
        if self.comp.mount_options:
            options += [ self.comp.mount_options ]

        # Mount options from command line
        if self.addopts:
            options += [ self.addopts ]

        if len(options):
            command.append("-o " + ','.join(options))

        # MGS NIDs
        # List of node nids ['foo1@tcp0,foo1@tcp1', 'foo2@tcp0,foo2@tcp1']
        nodenids = [','.join(nids) for nids in self.comp.fs.get_mgs_nids()]
        mgsfullnid = ':'.join(nodenids)
        command.append("%s:/%s" % (mgsfullnid, self.comp.fs.fs_name))

        command.append(mount_path)

        return command
