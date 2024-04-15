# StartTarget.py -- Lustre action class : start (mount) target
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
This module contains a FSAction class to start a Lustre target.
"""

import os

from ClusterShell.Task import task_self

from Shine.Configuration.Globals import Globals

from Shine.Lustre.Actions.Action import FSAction, Result

class StartTarget(FSAction):
    """
    File system target start action class.

    Lustre, since 1.6, starts a target simply by mounting it.
    """

    NAME = 'start'

    def __init__(self, target, **kwargs):
        FSAction.__init__(self, target, **kwargs)
        self.mount_options = kwargs.get('mount_options')
        self.mount_paths = kwargs.get('mount_paths')

    def _already_done(self):
        """Return a Result object is the target is already mounted."""

        # Already done?
        if self.comp.is_started():
            return Result("%s is already started" % self.comp.label)

        # LBUG #18624
        if not self.comp.dev_isblk:
            task_self().set_info("fanout", 1)

        return None

    def _prepare_cmd(self):
        """Mount file system target."""

        # If there is a user-defined path
        if self.mount_paths and self.comp.TYPE in self.mount_paths:
            mount_path = self.mount_paths[self.comp.TYPE]
        else:
            # Default mount path
            mount_path = "/mnt/$fs_name/$type/$index"

        # Replace variables
        var_map = {'index': str(self.comp.index),
                   'dev'  : os.path.basename(self.comp.dev)}
        if self.comp.journal:
            var_map['jdev'] = os.path.basename(self.comp.journal.dev)

        mount_path = self._vars_substitute(mount_path, var_map)

        #
        # Build command. Try both old and new Lustre FS types. The mount command
        # first tries to exec mount.lustre_tgt and fallback to mount.lustre if
        # not found. The lustre_tgt FS type is set in the first place as it is
        # more future proof.
        #
        command = ["mkdir -p \"%s\"" % mount_path]
        command += ["&& /bin/mount -t lustre_tgt,lustre"]

        # Loop devices handling
        if not self.comp.dev_isblk:
            command.append("-o loop")

        options = []
        # Mount options from configuration
        if self.mount_options and self.mount_options.get(self.comp.TYPE):
            options += [self.mount_options.get(self.comp.TYPE)]
        # Mount options from command line
        if self.addopts:
            options += [self.addopts]

        # When device detection order is variable, jdev could have a different
        # major/minor than the one it has on previous mount.
        # In this case, we must be sure we use the current one to avoid error.
        #
        # (Note: We can use `blkid' instead of jdev and extract the current
        # journal UUID if we have issue using directly jdev path.)
        if self.comp.journal:
            majorminor = os.stat(self.comp.journal.dev).st_rdev
            options += ["journal_dev=%#x" % majorminor]

        if len(options):
            command.append('-o ' + ','.join(options))

        command.append(self.comp.dev)
        command.append(mount_path)

        return command

    def needed_modules(self):
        if Globals().lustre_version_is_smaller('2.4') or \
           not Globals().lustre_version_is_smaller('2.5'):
            return ['lustre', 'ldiskfs']
        else:
            # lustre 2.4 needs fsfilt_ldiskfs
            return ['lustre', 'fsfilt_ldiskfs']
