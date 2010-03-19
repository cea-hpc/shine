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

import re

from Shine.Lustre.Actions.Action import Action

class StartTarget(Action):
    """
    File system target start action class.

    Current version of Lustre (1.6) starts a target simply by mounting it.
    """

    def __init__(self, target, **kwargs):
        Action.__init__(self)
        self.target = target
        assert self.target != None
        self.mount_options = kwargs.get('mount_options')
        self.mount_paths = kwargs.get('mount_paths')
        self.abort_recovery = kwargs.get('abort_recovery')

    def _substitute(self, template, mapping):
        """
        Performs the template substitution, returning a new string.
        mapping is any dictionary-like object with keys that match
        the placeholders in the template. 

        To get changed with Template.string.substitute in Python 2.4
        when the Python 2.3 compat constraint will be dropped.
        """

        # Do we have something which looks like a variable?
        m = re.search(r"\$([A-Za-z0-9_]+)", template)
        while m is not None:
            var = m.group(1)
            if var not in mapping:
                raise KeyError, var
            template = template.replace("$%s" % var, mapping[var])
            m = re.search("\$([A-Za-z0-9_]+)", template)
        return template

    def launch(self):
        """
        Mount file system target.
        """

        mount_path = None
        if self.mount_paths:
            mount_path = self.mount_paths.get(self.target.type)


            var_map = { 'fs_name' : self.target.fs.fs_name,
                        'index'   : str(self.target.index) }

            try:
                mount_path = self._substitute(mount_path, var_map)
            except KeyError, e:
                # Unknown variable in mount_path: failback to default
                pass

        if not mount_path:
            # fallback to defaut
            mount_path = "/mnt/%s/%s/%d" % (self.target.fs.fs_name,
                    self.target.type, self.target.index)

        command = ["mkdir", "-p", "\"%s\"" % mount_path]
        command += ["&&", "/sbin/modprobe", "lustre"]
        command += ["&&", "/bin/mount", "-t", "lustre"]

        # Loop devices handling
        if not self.target.dev_isblk:
            command.append("-o loop")

        # Other custom mount options
        if self.mount_options:
            mnt_opts = self.mount_options.get(self.target.type)
            if mnt_opts:
                command.append("-o")
                command.append(mnt_opts)

        command.append(self.target.dev)
        command.append(mount_path)

        self.task.shell(' '.join(command), handler=self)

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        self.target._lustre_check()

        if worker.did_timeout():
            # action timed out
            self.target._action_timeout("start")
        elif worker.retcode() == 0:
            # action succeeded
            self.target._action_done("start")
        else:
            # action failure
            self.target._action_failed("start", worker.retcode(), worker.read())

