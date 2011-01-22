# FSEventHandler.py -- Base Command Event Handler
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

import os
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

    def __init__(self, verbose=1):
        Shine.Lustre.EventHandler.EventHandler.__init__(self)
        self.verbose = verbose

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
    
    def _id_for_comp(self, comp_name, comp):
        # Ourgh, ugly hack to handle journal display!
        if comp_name == 'journal':
            return "%s journal (%s)" % (comp.get_id(), comp.jdev)
        else:
            return comp.longtext()

    def action_start(self, node, comp, comp_name=None):
        header = self.ACTIONING.capitalize()
        comp_id = self._id_for_comp(comp_name, comp)
        txt = "%s %s" % (header, comp_id)
        self.log_info(txt)

    def action_done(self, node, comp, comp_name=None):
        header = self.ACTION.capitalize()
        comp_id = self._id_for_comp(comp_name, comp)
        if comp.status_info:
            self.log_info("%s of %s: %s" % \
                   (header, comp_id, comp.status_info))
        else:
            self.log_info("%s of %s succeeded" % (header, comp_id))

    def action_failed(self, node, comp, rc, message, comp_name=None):
        comp_id = self._id_for_comp(comp_name, comp)
        if rc > 0 and not message:
            strerr = os.strerror(rc)
        else:
            strerr = message
        txt = "Failed to %s %s\n>> %s" % \
                 (self.ACTION, comp_id, strerr)
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

    def action_start(self, node, comp, comp_name=None):
        header = self.ACTIONING.capitalize()
        comp_id = self._id_for_comp(comp_name, comp)
        txt = "%s: %s %s" % (node, header, comp_id)
        self.log_verbose(txt)
        self.__update()

    def action_done(self, node, comp, comp_name=None):
        header = self.ACTION.capitalize()
        comp_id = self._id_for_comp(comp_name, comp)
        if comp.status_info:
            self.log_verbose("%s: %s of %s: %s" % \
                   (node, header, comp_id, comp.status_info))
        else:
            self.log_verbose("%s: %s of %s succeeded" % (node, header, comp_id))
        self.__update()

    def action_failed(self, node, comp, rc, message, comp_name=None):
        comp_id = self._id_for_comp(comp_name, comp)
        if rc > 0 and not message:
            strerr = os.strerror(rc)
        else:
            strerr = message
        txt = "%s: Failed to %s %s\n>> %s" % \
                 (node, self.ACTION, comp_id, strerr)
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
