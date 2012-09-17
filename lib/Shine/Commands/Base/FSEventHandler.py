# FSEventHandler.py -- Base Command Event Handler
# Copyright (C) 2009-2012 CEA
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

import datetime

# timer events
import ClusterShell.Event

# lustre events
import Shine.Lustre.EventHandler

from Shine.Lustre.FileSystem import INPROGRESS

from ClusterShell.Task import task_self



class FSLocalEventHandler(Shine.Lustre.EventHandler.EventHandler):

    ACTION = '<to_be_defined>'
    ACTIONING = '<to_be_defined>'

    def __init__(self, command, verbose=1):
        Shine.Lustre.EventHandler.EventHandler.__init__(self)
        self.command = command
        self.verbose = self.command.options.verbose

    #
    # Logging methods
    #

    def log_warning(self, msg):
        print msg

    def log_info(self, msg):
        if self.verbose > 0:
            print msg

    def log_verbose(self, msg):
        if self.verbose > 1:
            print msg
    
    def event_callback(self, compname, action, status, node, **kwargs):
        comp = kwargs['comp']
        if status == 'start':
            self.action_start(node, action, comp)
        elif status == 'done':
            result = kwargs.get('result', None)
            self.action_done(node, comp, result)
        elif status == 'timeout':
            self.action_timeout(node, comp)
        elif status == 'failed':
            result = kwargs['result']
            self.action_failed(node, comp, result)
        elif status == 'progress':
            result = kwargs['result']
            self.action_progress(node, comp, result)

    def log(self, txt):
        header = self.ACTIONING.capitalize()
        self.log_info("%s %s" % (header, txt))

    def action_start(self, node, action, comp):
        if action != 'proxy':
            self.log(comp.longtext())

    def action_done(self, node, comp, result):
        comp_id = comp.longtext()

        if result and result.duration >= 100:
            duration = " (%.1f min)" % (result.duration / 60.0)
        # start and stop sent Result message without duration when already done
        elif result and result.duration is not None:
            duration = " (%.1f sec)" % result.duration
        else:
            duration = ""

        if result and result.message:
            self.log("of %s%s: %s" % (comp_id, duration, result.message))
        else:
            self.log("of %s succeeded%s" % (comp_id, duration))

    def action_failed(self, node, comp, result):
        txt = "Failed to %s %s\n>> %s" % \
                                    (self.ACTION, comp.longtext(), str(result))
        self.log_warning(txt)


class FSGlobalEventHandler(FSLocalEventHandler,
        ClusterShell.Event.EventHandler):

    def __init__(self, verbose=1, fs_conf=None):
        ClusterShell.Event.EventHandler.__init__(self)
        FSLocalEventHandler.__init__(self, verbose)
        self.fs = None
        self.fs_conf = fs_conf
        self.action_timer = None
        self.last_target_count = 0
        self.status_changed = False

    def log(self, node, txt):
        header = self.ACTIONING.capitalize()
        self.log_verbose("%s: %s %s" % (node, header, txt))

    def action_start(self, node, action, comp):
        if action != 'proxy':
            self.log(node, comp.longtext())
        self.__update()

    def action_done(self, node, comp, result):
        header = self.ACTION.capitalize()
        comp_id = comp.longtext()

        if result and result.duration >= 100:
            duration = " (%.1f min)" % (result.duration / 60.0)
        # start and stop sent Result message without duration when already done
        elif result and result.duration is not None:
            duration = " (%.1f sec)" % result.duration
        else:
            duration = ""

        if result and result.message:
            self.log_verbose("%s: %s of %s%s: %s" % \
                             (node, header, comp_id, duration, result.message))
        else:
            self.log_verbose("%s: %s of %s succeeded%s" %
                             (node, header, comp_id, duration))
        self.__update()

    def action_failed(self, node, comp, result):
        txt = "Failed to %s %s\n>> %s" % \
                                    (self.ACTION, comp.longtext(), str(result))
        # Add nodename prefix
        txt = ''.join(["%s: %s" % (node, line)
                       for line in txt.splitlines(True)])
        self.log_warning(txt)
        self.__update()

    def handle_pre(self, fs):
        """
        Default pre-handler. Display a single line.
        """
        header = self.ACTIONING.capitalize()
        comps = fs.components.managed(supports=self.ACTION)
        self.log_verbose("%s %d component(s) of %s on %s" % (header, len(comps),
                            fs.fs_name, comps.servers()))

    def handle_post(self, fs):
        pass

    def pre(self, fs):
        # attach fs to this handler
        self.fs = fs
        self.handle_pre(fs)
        self.__update()

    def post(self, fs):
        self.handle_post(fs)

    def ev_timer(self, timer):
        """
        Repeating timer callback for in-progress operations.
        """

        filter_key = lambda t: t.state == INPROGRESS or t._list_action()
        targets = self.fs.components.managed().filter(key=filter_key)
        target_servers = targets.servers()
        target_count = len(targets)

        if target_count > 0 and self.status_changed:
            self.status_changed = False
            now = datetime.datetime.now()
            if len(target_servers) > 8:
                print "[%s] In progress for %d component(s) on %d servers ..." \
                    % (now.strftime("%H:%M"), target_count, len(target_servers))
            else:
                print "[%s] In progress for %d component(s) on %s ..." % \
                        (now.strftime("%H:%M"), target_count, target_servers)

    def __update(self):
        self.status_changed = True
        # (re)start timer if needed
        if self.verbose > 0 and (not self.action_timer or not self.action_timer.is_valid()):
            # timer on
            self.action_timer = task_self().timer(2.0, handler=self, interval=20, autoclose=True)
            assert self.action_timer != None
