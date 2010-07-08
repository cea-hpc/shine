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

# timer events
import ClusterShell.Event

# lustre events
import Shine.Lustre.EventHandler

from Shine.Lustre.FileSystem import INPROGRESS

from ClusterShell.Task import task_self
from ClusterShell.NodeSet import NodeSet

import datetime


class FSGlobalEventHandler(Shine.Lustre.EventHandler.EventHandler,
        ClusterShell.Event.EventHandler):

    def __init__(self, verbose=1, fs_conf=None):
        Shine.Lustre.EventHandler.EventHandler.__init__(self)
        ClusterShell.Event.EventHandler.__init__(self)
        self.fs = None
        self.fs_conf = fs_conf
        self.verbose = verbose
        self.action_timer = None
        self.last_target_count = 0
        self.status_changed = False

    def pre(self, fs):
        # attach fs to this handler
        self.fs = fs
        self.handle_pre(fs)
        self.update()

    def post(self, fs):
        self.handle_post(fs)

    def ev_timer(self, timer):
        """
        Repeating timer callback for in-progress operations.
        """

        filter_key = lambda t: t.state == INPROGRESS or t._list_action()
        targets = list(self.fs.managed_components(filter_key=filter_key))
        target_servers = NodeSet.fromlist([t.server for t in targets])
        target_count = len(targets)

        if target_count > 0:
            if self.status_changed:
                self.status_changed = False
                now = datetime.datetime.now()
                print "[%s] In progress for %d component(s) on %s ..." % \
                        (now.strftime("%H:%M"), target_count, target_servers)

    def update(self):
        self.status_changed = True
        # (re)start timer if needed
        if self.verbose > 0 and (not self.action_timer or not self.action_timer.is_valid()):
            # timer on
            self.action_timer = task_self().timer(2.0, handler=self, interval=20, autoclose=True)
            assert self.action_timer != None
