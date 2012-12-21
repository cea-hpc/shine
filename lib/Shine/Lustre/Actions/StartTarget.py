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

from Shine.Lustre.Actions.Action import FSAction

class StartTarget(FSAction):
    """
    File system target start action class.

    Current version of Lustre (1.6) starts a target simply by mounting it.
    """

    NAME = 'start'

    def __init__(self, target, **kwargs):
        FSAction.__init__(self, target, **kwargs)
        self.mount_options = kwargs.get('mount_options')
        self.mount_paths = kwargs.get('mount_paths')

    def _vars_substitute(self, txt, suppl_vars=None):
        """
        Replace symbolic variable from the provided text.

        This function extends FSAction._var_substitute. It adds:
         $index
         $dev:     Replaced by the basename of the device.
         $jdev:    Same as 'dev' for the journal device.
        """
        var_map = {
                    'index'   : str(self.comp.index),
                    'dev'     : os.path.basename(self.comp.dev),
                  }

        if self.comp.journal:
            var_map['jdev'] = os.path.basename(self.comp.journal.dev)

        if suppl_vars:
            var_map.update(suppl_vars)

        return FSAction._vars_substitute(self, txt, var_map)

    def _prepare_cmd(self):
        """Mount file system target."""

        # If there is a user-defined path
        if self.mount_paths and self.comp.TYPE in self.mount_paths:
            mount_path = self.mount_paths[self.comp.TYPE]
        else:
            # Default mount path
            mount_path = "/mnt/$fs_name/$type/$index"

        # Replace variables
        mount_path = self._vars_substitute(mount_path)

        #
        # Build command
        #
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
        if self.comp.journal:
            majorminor = os.stat(self.comp.journal.dev).st_rdev
            options += [ "journal_dev=%#x" % majorminor ]

        if len(options):
            command.append('-o ' + ','.join(options))

        command.append(self.comp.dev)
        command.append(mount_path)

        return command
