# Action.py -- Abstract class for shine lustre action
# Copyright (C) 2007 CEA
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

"""
Actions classes defined the code to launch and the event handler for a specific
action.

An action must inherits from one of the base Action class.
"""

from ClusterShell.Event import EventHandler
from ClusterShell.Task import task_self

class Action(EventHandler):
    """
    Generic abstract Shine action.
    """

    def __init__(self, task=task_self()):
        EventHandler.__init__(self)
        self.task = task

    def launch(self):
        """
        Run the action.
        """
        raise NotImplementedError("Derived classes must implement.")


class FSAction(Action):
    """
    Astract Shine action class for FileSystem actions.
    """

    NAME = "(to be changed)"

    def __init__(self, comp, task=task_self(), **kwargs):
        Action.__init__(self, task)
        self.comp = comp

    def _prepare_cmd(self):
        """
        Return an array of command and arguments to be run to be run by launch()
        method.
        """
        raise NotImplementedError("Derived classes must implement it.")

    def launch(self):
        """
        Create a command line and schedule it to be run by self.task.
        """

        # Extent path
        command = [ "export PATH=/usr/lib/lustre:$PATH;" ]

        # Call specific method to prepare command line
        command += self._prepare_cmd()

        # Add the command to be scheduled
        cmdline = ' '.join(command)

        # XXX: Add timeout
        self.task.shell(cmdline, handler=self)

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        self.comp.lustre_check()

        # Action timed out
        if worker.did_timeout():
            self.comp._action_timeout(self.NAME)

        # Action succeeded
        elif worker.retcode() == 0:
            self.comp._action_done(self.NAME)

        # Action failed
        else:
            self.comp._action_failed(self.NAME, worker.retcode(), worker.read())
