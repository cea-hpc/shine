# StopTarget.py -- Lustre action class : stop (umount) target
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

from Shine.Lustre.Actions.Action import Action

class StopTarget(Action):
    """
    File system target start action class.

    Current version of Lustre (1.6) starts a target simply by mounting it.
    """

    def __init__(self, target, **kwargs):
        Action.__init__(self)
        self.target = target
        assert self.target != None

    def launch(self):
        """
        Unmount file system target.
        """

        command = ["umount"]

        # Also free the loop device if needed
        if not self.target.dev_isblk:
            command.append("-d")

        command.append(self.target.mntdev)

        self.task.shell(' '.join(command), handler=self)

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        self.target._lustre_check()

        if worker.did_timeout():
            # action timed out
            self.target._action_timeout("stop")
        elif worker.retcode() == 0:
            # action succeeded
            self.target._action_done("stop")
        else:
            # action failure
            self.target._action_failed("stop", worker.retcode(), worker.read())

