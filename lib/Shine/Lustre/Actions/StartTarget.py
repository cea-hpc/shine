# StartTarget.py -- Lustre action class : start (mount) target
# Copyright (C) 2009 CEA
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

import os
from string import Template

from Shine.Lustre.Actions.Action import FSAction

class StartTarget(FSAction):
    """
    File system target start action class.

    Current version of Lustre (1.6) starts a target simply by mounting it.
    """

    NAME = 'start'

    def __init__(self, target, **kwargs):
        FSAction.__init__(self, target)
        self.mount_options = kwargs.get('mount_options')
        self.addopts = kwargs.get('addopts')
        self.mount_paths = kwargs.get('mount_paths')

    def _prepare_cmd(self):
        """Mount file system target."""

        mount_path = None
        if self.mount_paths:
            mount_path = self.mount_paths.get(self.comp.TYPE)

            var_map = { 'fs_name' : self.comp.fs.fs_name,
                        'label'   : self.comp.label,
                        'type'    : self.comp.TYPE,
                        'index'   : str(self.comp.index) }

            try:
                mount_path = Template(mount_path).substitute(var_map)
            except KeyError:
                # Unknown variable in mount_path: failback to default
                pass

        if not mount_path:
            # fallback to defaut
            mount_path = "/mnt/%s/%s/%d" % (self.comp.fs.fs_name,
                    self.comp.TYPE, self.comp.index)

        command = ["mkdir -p \"%s\"" % mount_path]
        command += ["&& /bin/mount -t lustre"]

        # Loop devices handling
        if not self.comp.dev_isblk:
            command.append("-o loop")

        options = []
        # Mount options from configuration
        if self.mount_options and self.mount_options.get(self.comp.TYPE):
            options += [ self.mount_options.get(self.comp.TYPE) ]
        # Mount options from command line
        if self.addopts:
            options += [ self.addopts ]

        # When device detection order is variable, jdev could have a different
        # major/minor than the one it has on previous mount.
        # In this case, we must be sure we use the current one to avoid error.
        #
        # (Note: We can use `blkid' instead of jdev and extract the current
        # journal UUID if we have issue using directly jdev path.)
        if self.comp.jdev:
            majorminor = os.stat(self.comp.jdev).st_rdev
            options += [ "journal_dev=%#x" % majorminor ]

        if len(options):
            command.append('-o ' + ','.join(options))

        command.append(self.comp.dev)
        command.append(mount_path)

        return command
