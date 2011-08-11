# StartClient.py -- Mount client
# Copyright (C) 2009, 2010 CEA
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

from Shine.Lustre.Actions.Action import FSAction

class StartClient(FSAction):
    """
    File system client start (ie. mount) action class.
    """

    NAME = 'mount'

    def __init__(self, client, **kwargs):
        FSAction.__init__(self, client)
        self.mount_options = kwargs.get('mount_options')
        self.addopts = kwargs.get('addopts')

    def _prepare_cmd(self):
        """
        Prepare client file system mount command line.
        """

        mount_path = self._vars_substitute(self.comp.mount_path)

        command = ["mkdir -p \"%s\"" % mount_path]
        command += ["&& /bin/mount -t lustre"]

        options = []

        # Mount options from configuration
        if self.mount_options:
            options += [ self.mount_options ]

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
