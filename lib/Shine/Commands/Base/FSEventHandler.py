# FSEventHandler.py -- Base Command Event Handler
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
Command event handler classes used to display information when receiving events.
"""

import datetime

from ClusterShell.Task import task_self

from Shine.CLI.Display import display
from Shine.Lustre.EventHandler import EventHandler as LustreEH
from Shine.Lustre.FileSystem import INPROGRESS


STATUS_TO_TXT = {
    'start':    ' ...',
    'done':     ' succeeded',
    'timeout':  ' has timeout',
    'failed':   ' failed',
    'progress': ' is in progress',
}

class FSLocalEventHandler(LustreEH):
    """
    Command event handler used when Shine is called for a local
    processing only (-L).
    """

    SUMMARY = True

    def __init__(self, command):
        LustreEH.__init__(self)
        self.command = command
        # Name of action to be supported by components (used with filter())
        self.fs_action = command.NAME
        self.verbose = self.command.options.verbose
        self.fs = None

    #
    # Logging methods
    #

    def log_warning(self, msg):
        """Display a warning message."""
        print msg

    def log_info(self, msg):
        """Display an informative message, only if verbosity is not 0."""
        if self.verbose > 0:
            print msg

    def log_verbose(self, msg):
        """Display a verbose message. Verbosity should be 2 or above."""
        if self.verbose > 1:
            print msg

    def log(self, _node, action, comptxt, status):
        """Display a standard message giving the status of action component."""
        status = STATUS_TO_TXT.get(status, status)
        self.log_info("%s of %s%s" % (action.capitalize(), comptxt, status))

    #
    # Event handlers
    #

    def action_start(self, node, action, comp):
        """Display a message when a component action is started."""
        if action != 'proxy':
            self.log(node, action, comp.longtext(), 'start')

    def action_done(self, node, action, comp, result):
        """Display a message when a component action is finished."""
        if action == 'proxy':
            return

        if result and result.duration >= 100:
            duration = " (%.1f min)" % (result.duration / 60.0)
        # start and stop sent Result message without duration when already done
        elif result and result.duration is not None:
            duration = " (%.1f sec)" % result.duration
        else:
            duration = ""

        if result and result.message:
            self.log(node, action, comp.longtext(),
                     "%s: %s" % (duration, result.message))
        else:
            self.log(node, action, comp.longtext(), ' succeeded%s' % duration)

    def action_failed(self, _node, action, comp, result):
        """Display a warning message when a component action failed."""
        txt = "%s of %s failed\n>> %s" % (action, comp.longtext(), str(result))
        self.log_warning(txt)

    def action_timeout(self, node, action, comp):
        """No-op when a component action timeout."""

    def action_progress(self, node, action, comp, result):
        """No-op when a component action progress is received."""

    def event_callback(self, compname, action, status, **kwargs):
        node = kwargs['node']
        comp = kwargs['comp']
        if status == 'start':
            self.action_start(node, action, comp)
        elif status == 'done':
            result = kwargs.get('result', None)
            self.action_done(node, action, comp, result)
        elif status == 'timeout':
            self.action_timeout(node, action, comp)
        elif status == 'failed':
            result = kwargs['result']
            self.action_failed(node, action, comp, result)
        elif status == 'progress':
            result = kwargs['result']
            self.action_progress(node, action, comp, result)

    def handle_pre(self):
        """Custom handler called before processing each filesystem."""
        pass

    def pre(self, fs):
        """
        Attach the provided filesystem to this handler for further processing.
        """
        self.fs = fs
        self.handle_pre()

    def handle_post(self, fs):
        """
        Custom handler called after processing each filesystem.

        It displays a table summary if verbosity is high enough and
        SUMMARY is set for this command (True by default).
        """
        if self.SUMMARY and self.verbose > 0:
            print display(self.command, fs, supports=self.fs_action)

    def post(self, fs):
        """Do any post-processing. This is called for each filesystem."""
        self.handle_post(fs)


# Theorically, this class should inherit from ClusterShell EventHandler too.
# But, at this class is only an interface, with no code, it is useless.
# This avoids this class having too many methods.
# Change this is CS EventHandler evolve.

class FSGlobalEventHandler(FSLocalEventHandler):
    """
    Command event handler used when Shine is called for a global (admin)
    processing.

    This means local and distant commands could be executed.
    """

    def __init__(self, command):
        FSLocalEventHandler.__init__(self, command)
        self._timer = None
        self.status_changed = False

    def log(self, node, action, comptxt, status):
        """Display a standard message giving the status of action component."""
        status = STATUS_TO_TXT.get(status, status)
        self.log_verbose("%s: %s of %s%s" % (node, action.capitalize(),
                                             comptxt, status))

    def action_failed(self, node, action, comp, result):
        txt = "%s of %s failed\n>> %s" % (action, comp.longtext(), str(result))
        # Add nodename prefix
        txt = ''.join(["%s: %s" % (node, line)
                       for line in txt.splitlines(True)])
        self.log_warning(txt)

    def event_callback(self, compname, action, status, **kwargs):
        FSLocalEventHandler.event_callback(self, compname, action, status,
                                           **kwargs)

        if status in ('start', 'done', 'failed'):
            self._update()


    def handle_pre(self):
        """Default pre-handler. Display a single line."""
        header = self.command.NAME.capitalize()
        comps = self.fs.components.managed(supports=self.fs_action)
        self.log_verbose("%s of %d component(s) of %s on %s" %
                         (header, len(comps), self.fs.fs_name, comps.servers()))

    def pre(self, fs):
        FSLocalEventHandler.pre(self, fs)
        self._update()


    def ev_timer(self, timer):
        """Repeating timer callback for in-progress operations."""
        filter_key = lambda t: t.state == INPROGRESS or t._list_action()
        targets = self.fs.components.managed().filter(key=filter_key)
        target_servers = targets.servers()
        target_count = len(targets)

        if target_count > 0 and self.status_changed:
            self.status_changed = False
            now = datetime.datetime.now().strftime("%H:%M")
            if len(target_servers) > 8:
                print "[%s] In progress for %d component(s) on %d servers ..." \
                    % (now, target_count, len(target_servers))
            else:
                print "[%s] In progress for %d component(s) on %s ..." % \
                      (now, target_count, target_servers)

    def _update(self):
        """
        Called each time an event is received, it enable a timer used for
        display.
        """
        self.status_changed = True
        # (re)start timer if needed
        if self.verbose > 0 and not (self._timer and self._timer.is_valid()):
            self._timer = task_self().timer(2.0, handler=self, interval=20,
                                            autoclose=True)
            assert self._timer != None
