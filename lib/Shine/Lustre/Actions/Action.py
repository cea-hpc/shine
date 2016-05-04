# Action.py -- Abstract class for shine lustre action
# Copyright (C) 2007-2015 CEA
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

# Possible values for mountdata
MOUNTDATA_NEVER  = 0
MOUNTDATA_AUTO   = 1
MOUNTDATA_ALWAYS = 2

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

class ActionInfo(object):
    """Information describing an action event."""

    def __init__(self, action, elem=None, description=None):
        self.actname = action.NAME
        self.elem = elem
        self.description = description

    def __str__(self):
        return self.description or self.actname


class Action(EventHandler):
    """
    Generic abstract Shine action.
    """

    NAME = "(to be changed)"

    def __init__(self):
        EventHandler.__init__(self)
        self.task = task_self()

        # Action duration
        self.start = None
        self.duration = None

    def info(self):
        """Return a ActionInfo describing this action."""
        return ActionInfo(self, None)

    def ev_start(self, worker):
        """Store the start time."""
        self.start = time.time()

    def ev_close(self, worker):
        """Compute the action whole duration."""
        self.duration = time.time() - self.start

    def launch(self):
        """Run the action."""
        raise NotImplementedError("Derived classes must implement.")

class CommonAction(Action):
    """
    Abstract class representing an Action with graph dependency features.

    It could be with other CommonAction instances to create a graph of actions.
    See GroupAction to group them.
    """

    def __init__(self):
        Action.__init__(self)
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

    def launch(self):
        """Check dependencies and run the action."""

        if not self._graph_ok(self.deps):
            return

        self.set_status(ACT_RUNNING)
        self._launch()

    def _launch(self):
        """
        Really starts the action, without graph involvement.

        Need to be overloaded in child class.
        """
        raise NotImplementedError


class ActionGroup(CommonAction):
    """
    Group several CommonAction to create a common entity which could be used
    inside a graph of CommonAction or ActionGroup.
    """

    def __init__(self):
        CommonAction.__init__(self)
        self._members = list()  # Ideally this should be an OrderedSet

    def __len__(self):
        """Number or group members."""
        return len(self._members)

    def __iter__(self):
        """Iterate over group members."""
        return iter(self._members)

    def __getitem__(self, idx):
        """Get element at index `idx'."""
        return self._members[idx]

    def add(self, action):
        """Add an action to this group."""
        if action not in self._members:  # _members should behave like a set
            self._members.append(action)
            # Add a half-dependency
            action.followers.add(self)

    def sequential(self):
        """Create a dependency between each group element.

        This will make a chain of dependencies, removing all possible
        parallelism between group members.
        """
        for elem1, elem2 in zip(self._members, self._members[1:]):
            elem2.depends_on(elem1)

    def _launch(self):
        """Launch each member of this group."""
        # _graph_ok() wants us WAITING but launch() set us RUNNING
        self.set_status(ACT_WAITING)

        if not self._graph_ok(self._members):
            return

        # So, all members are OK
        self.set_status(ACT_OK)


class FSAction(CommonAction):
    """
    Astract Shine action class for FileSystem actions.
    """

    # full_check() should also check mountdata?
    CHECK_MOUNTDATA = MOUNTDATA_AUTO

    NEEDED_MODULES = []

    def __init__(self, comp, **kwargs):
        CommonAction.__init__(self)
        self.comp = comp

        # Command should have a separate stderr?
        self.stderr = False

        self.dryrun = kwargs.get('dryrun', False)

        self.addopts = self._addopts_substitute(kwargs.get('addopts'))

        # If mountdata is not set, use the default value of each action.
        ck_mntdata = {
            'never':  MOUNTDATA_NEVER,
            'auto':   self.__class__.CHECK_MOUNTDATA,
            'always': MOUNTDATA_ALWAYS,
        }
        self.check_mountdata = ck_mntdata[kwargs.get('mountdata', 'auto')]

    def info(self):
        """Return a ActionInfo describing this action."""
        desc = '%s of %s' % (self.NAME, self.comp.longtext())
        return ActionInfo(self, self.comp, desc)

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

        self.comp.fs.hdlr.log('detail', msg='[RUN] %s' % cmdline)

        if self.dryrun:
            self.comp.action_event(self, 'done')
            self.set_status(ACT_OK)
        else:
            self.task.shell(cmdline, handler=self, stderr=self.stderr)

    def _launch(self):
        """
        Run the command to process the action.

        It checks the command could be really be run and raises events.
        """
        self.comp.action_event(self, 'start')
        try:
            self.comp.full_check(mountdata=self.check_mountdata)

            result = self._already_done()
            if not result:
                self._shell()
            else:
                self.comp.action_event(self, 'done', result)
                self.set_status(ACT_OK)

        except ComponentError, error:
            self.comp.action_event(self, 'failed', Result(str(error)))
            self.set_status(ACT_ERROR)

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        Action.ev_close(self, worker)

        self.comp.lustre_check()

        # Action timed out
        if worker.did_timeout():
            self.comp.action_event(self, 'timeout')
            self.set_status(ACT_ERROR)

        # Action succeeded
        elif worker.retcode() == 0:
            result = Result(duration=self.duration, retcode=worker.retcode())
            self.comp.action_event(self, 'done', result)
            self.set_status(ACT_OK)

        # Action failed
        else:
            result = ErrorResult(worker.read(), self.duration, worker.retcode())
            self.comp.action_event(self, 'failed', result)
            self.set_status(ACT_ERROR)

    def needed_modules(self):
        """
        Some modules may need to be loaded before this action is performed.
        The module list depends on the action and the component.
        """
        return self.NEEDED_MODULES
