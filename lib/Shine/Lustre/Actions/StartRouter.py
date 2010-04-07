# StartRouter.py -- Start router
# Copyright (C) 2010 CEA
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

class StartRouter(Action):
    """
    File system router (ie: start lnet) start class
    """

    def __init__(self, router):
        Action.__init__(self)
        self._router = router
        assert self._router != None

    def launch(self):
        """
        Start LNET
        """
        command = [ "export PATH=/usr/lib/lustre:$PATH;" ]
        command += ["/sbin/modprobe", "lnet"]
        command += ["&&", "lctl", "net", "up"]

        self.task.shell(' '.join(command), handler=self) ### timeout

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        self._router._router_check()

        if worker.did_timeout():
            # action timed out
            self._router._action_timeout("start")
        elif worker.retcode() == 0:
            # action succeeded
            self._router._action_done("start")
        else:
            # action failure
            self._router._action_failed("start", worker.retcode(), 
                                        worker.read())
