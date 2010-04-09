# Fsck.py -- Lustre action class : fsck
# Copyright (C) 2010 BULL S.A.S
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
from Shine.Lustre.Component import TARGET_ERROR

class Fsck(Action):
    """
    File system fsck action class.
    """

    def __init__(self, target, **kwargs):
        Action.__init__(self)
        self.target = target
        self.addopts = kwargs.get('addopts')
        assert self.target != None

    def launch(self):
        command = ["export PATH=/usr/lib/lustre:$PATH;", "e2fsck", '-y', self.target.dev]

        # Process additional options
        if self.addopts:
            command.append(self.addopts)

        self.task.shell(' '.join(command), handler=self)

    def ev_close(self, worker):
        self.target._lustre_check()

        if worker.did_timeout():
            # action timed out
            self.target._action_timeout('fsck')
        # fsck returns 0=NOERROR, 1=OK_BUT_CORRECTION, 2=OK_BUT_REBOOT.
        # see man fsck.
        elif worker.retcode() in (0, 1, 2):
            # action succeeded
            self.target._action_done('fsck')
        else:
            # action failure
            self.target.state = TARGET_ERROR
            self.target._action_failed('fsck', worker.retcode(), worker.read())
