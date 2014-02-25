# Action.py -- Abstract class for shine lustre action
# Copyright (C) 2007-2013 CEA
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
Actions classes defined the code to launch and the event handler for a specific
action.

An action must inherits from one of the base Action class.
"""

import os
import time
import re
from string import Template

from ClusterShell.Event import EventHandler
from ClusterShell.Task import task_self

from Shine.Configuration.Globals import Globals

from Shine.Lustre import ComponentError

# XXX: This is not really good to import stuff from CLI in Actions. This part
# of Display should be generalized in some kind of Utility module and imported
# in Display and Action.
from Shine.CLI.Display import map_field

# Action possible states
ACT_WAITING = 0
ACT_RUNNING = 1
ACT_OK = 2
ACT_ERROR = 3


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

class CommonAction(Action):
    """
    Abstract class representing an Action with graph dependency features.

    It could be with other CommonAction instances to create a graph of actions.
    See GroupAction to group them.
    """

    def __init__(self, task=task_self()):
        Action.__init__(self, task)
        self.deps = set()
        self.followers = set()
        self._status = ACT_WAITING

    def depends_on(self, other):
        """
        Add a dependency on `other'.

        This action should not be launched before `other' is run with success.
        """
        self.deps.add(other)
        other.followers.add(self)

    def status(self):
        """Return current action status."""
        return self._status

    def set_status(self, status):
        """
        Update action status.

        If this is a final state, try to launch actions depending on it.
        """
        self._status = status
        # If it is a final states, propagate in the graph
        if self._status in (ACT_OK, ACT_ERROR):
            for action in self.followers:
                action.launch()

    def _launch(self):
        """
        Really starts the action, without graph involvement.

        Need to be overloaded in child class.
        """
        raise NotImplemented()

    def _graph_ok(self, actions):
        """
        Return True if dependencies in action list are OK.

        Return False if
         - the group is not in WAITING state.
         - one of them is waiting and launch it
         - one of them is still running
         - one of them is in error. This group is set in ERROR too.
        """

        # If I'm no more waiting, no need to be launched twice
        if self.status() != ACT_WAITING:
            return False

        # If some deps are not yet run, launch them!
        waiting = [dep for dep in actions if dep.status() == ACT_WAITING]
        if waiting:
            for dep in waiting:
                dep.launch()
            return False

        # If all my deps are not in final state, wait
        running = [dep for dep in actions if dep.status() == ACT_RUNNING]
        if running:
            return False

        # If some deps are in error, I'm too
        error = [dep for dep in actions if dep.status() == ACT_ERROR]
        if error:
            self.set_status(ACT_ERROR)
            return False

        return True

    def launch(self):
        """Check dependencies and run the action."""

        if not self._graph_ok(self.deps):
            return

        self.set_status(ACT_RUNNING)
        self._launch()

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        Action.ev_close(self, worker)

        # Action timed out
        if worker.did_timeout():
            self.set_status(ACT_ERROR)

        # Action succeeded
        elif worker.retcode() == 0:
            self.set_status(ACT_OK)

        # Action failed
        else:
            self.set_status(ACT_ERROR)


class ActionGroup(CommonAction):
    """
    Group several CommonAction to create a common entity which could be used
    inside a graph of CommonAction or ActionGroup.
    """

    def __init__(self, task=task_self()):
        CommonAction.__init__(self, task)
        self._members = set()

    def __len__(self):
        """Number or group members."""
        return len(self._members)

    def add(self, action):
        """Add an action to this group."""
        self._members.add(action)
        # Add a half-dependency
        action.followers.add(self)

    def launch(self):
        """Check dependencies and run the action."""

        if not self._graph_ok(self.deps):
            return

        if not self._graph_ok(self._members):
            return

        # So, all members are OK
        self.set_status(ACT_OK)


class FSAction(CommonAction):
    """
    Astract Shine action class for FileSystem actions.
    """

    NAME = "(to be changed)"

    # full_check() should also check mountdata?
    CHECK_MOUNTDATA = True

    NEEDED_MODULES = []

    def __init__(self, comp, task=task_self(), **kwargs):
        CommonAction.__init__(self, task)
        self.comp = comp

        # Command should have a separate stderr?
        self.stderr = False

        self.addopts = self._addopts_substitute(kwargs.get('addopts'))

        # If mountdata is not set, use the default value of each action.
        if kwargs.get('mountdata', 'auto') != 'auto':
            # 'always' for True, 'never' for False
            self.check_mountdata = (kwargs['mountdata'] == 'always')
        else:
            self.check_mountdata = self.__class__.CHECK_MOUNTDATA

    def _addopts_substitute(self, addopts):
        """Substitute placeholders in `addopts' based on self.comp data."""

        re_pattern = '%([a-z]+)'
        if addopts is None:
            return None

        def replacer(matched):
            """Extract field name from the regexp and call map_field() for it"""
            return map_field(self.comp, matched.group(1), dash=False)
        return re.sub(re_pattern, replacer, addopts)

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

    def _already_done(self):
        """
        Verify if the action work is already done.

        Return a Result object if done, None otherwise.
        """
        return None

    def _shell(self):
        """Create a command line and schedule it to be run by self.task"""

        # Call specific method to prepare command line
        command = self._prepare_cmd()

        # Extent path if defined
        path = Globals().get('command_path')
        if path:
            command.insert(0, "export PATH=%s:${PATH};" % path)

        # Add the command to be scheduled
        cmdline = ' '.join(command)

        # XXX: Add timeout
        self.task.shell(cmdline, handler=self, stderr=self.stderr)

    def _launch(self):
        """
        Run the command to process the action.

        It checks the command could be really be run and raises events.
        """
        self.comp.action_start(self.NAME)
        try:
            self.comp.full_check(mountdata=self.check_mountdata)

            result = self._already_done()
            if not result:
                self._shell()
            else:
                self.set_status(ACT_OK)
                self.comp.action_done(self.NAME, result)

        except ComponentError, error:
            self.set_status(ACT_ERROR)
            self.comp.action_failed(self.NAME, Result(str(error)))

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        Action.ev_close(self, worker)

        self.comp.lustre_check()

        # Action timed out
        if worker.did_timeout():
            self.comp.action_timeout(self.NAME)
            self.set_status(ACT_ERROR)

        # Action succeeded
        elif worker.retcode() == 0:
            result = Result(duration=self.duration, retcode=worker.retcode())
            self.comp.action_done(self.NAME, result)
            self.set_status(ACT_OK)

        # Action failed
        else:
            result = ErrorResult(worker.read(), self.duration, worker.retcode())
            self.comp.action_failed(self.NAME, result)
            self.set_status(ACT_ERROR)

    def needed_modules(self):
        """
        Some modules may need to be loaded before this action is performed.
        The module list depends on the action and the component.
        """
        return self.NEEDED_MODULES
