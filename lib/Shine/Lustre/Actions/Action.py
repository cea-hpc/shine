# Action.py -- Abstract class for shine lustre action
# Copyright (C) 2007-2012 CEA
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

import os
import time
from string import Template

from ClusterShell.Event import EventHandler
from ClusterShell.Task import task_self

class Result(object):
    """
    Data associated to an Event.
    """

    def __init__(self, message=None, duration=None, retcode=None):
        self.message = message
        self.duration = duration
        self.retcode = retcode

    def __str__(self):
        return str(self.message)

class ErrorResult(Result):
    """
    Result for an error event. Contains the command return code.
    """

    def __str__(self):
        if not self.message and self.retcode is not None:
            return os.strerror(self.retcode)
        else:
            return Result.__str__(self)

class Action(EventHandler):
    """
    Generic abstract Shine action.
    """

    NAME = "(to be changed)"

    def __init__(self, task=task_self()):
        EventHandler.__init__(self)
        self.task = task

        # Action duration
        self.start = None
        self.duration = None

    def launch(self):
        """Run the action."""
        raise NotImplementedError("Derived classes must implement.")

    def ev_start(self, worker):
        """Store the start time."""
        self.start = time.time()

    def ev_close(self, worker):
        """Compute the action whole duration."""
        self.duration = time.time() - self.start


class FSAction(Action):
    """
    Astract Shine action class for FileSystem actions.
    """

    NAME = "(to be changed)"

    def __init__(self, comp, task=task_self(), **kwargs):
        Action.__init__(self, task)
        self.comp = comp

    def _vars_substitute(self, txt, suppl_vars=None):
        """
        Replace symbolic variable from the provided text.

        Supported variables are:
         $fs_name
         $label
         $type
        """
        var_map = { 'fs_name' : self.comp.fs.fs_name,
                    'label'   : self.comp.label,
                    'type'    : self.comp.TYPE,
                  }

        if suppl_vars:
            var_map.update(suppl_vars)

        # Unknown variable in mount_path: failback to default
        return Template(txt).safe_substitute(var_map)

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
        Action.ev_close(self, worker)

        self.comp.lustre_check()

        # Action timed out
        if worker.did_timeout():
            self.comp._action_timeout(self.NAME)

        # Action succeeded
        elif worker.retcode() == 0:
            result = Result(duration=self.duration, retcode=worker.retcode())
            self.comp._action_done(self.NAME, result)

        # Action failed
        else:
            result = ErrorResult(worker.read(), self.duration, worker.retcode())
            self.comp._action_failed(self.NAME, result)
