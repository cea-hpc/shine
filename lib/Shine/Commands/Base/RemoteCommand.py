# RemoteCommand.py -- Base command with remote capabilities
# Copyright (C) 2008, 2009 CEA
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *
from Command import Command
from RemoteCallEventHandler import RemoteCallEventHandler
from Support.Nodes import Nodes

import socket


class RemoteCommand(Command):
    
    def __init__(self):
        Command.__init__(self)
        self.remote_call = False
        self.local_flag = False
        attr = { 'optional' : True, 'hidden' : True }
        self.add_option('L', None, attr, cb=self.parse_L)
        self.add_option('R', None, attr, cb=self.parse_R)
        self.nodes_support = Nodes(self)
        self.eventhandler = None

    def parse_L(self, opt, arg):
        self.local_flag = True

    def parse_R(self, opt, arg):
        self.remote_call = True

    def has_local_flag(self):
        return self.local_flag or self.remote_call

    def init_execute(self):
        """
        Initialize execution of remote command, if needed. Should be called
        first from derived classes before really executing the command.
        """
        # Limit the scope of the command if called with local flag (-L) or
        # called remotely (-R).
        if self.has_local_flag():
            self.opt_n = socket.gethostname().split('.', 1)[0]

    def install_eventhandler(self, local_eventhandler, global_eventhandler):
        """
        Select and install the appropriate event handler.
        """
        if self.remote_call:
            # When called remotely (-R), install a special event handler
            # that knows how to speak the Shine Proxy Protocol using pickle.
            self.eventhandler = RemoteCallEventHandler()
        elif self.local_flag:
            self.eventhandler = local_eventhandler
        else:
            self.eventhandler = global_eventhandler
        # return handler for convenience
        return self.eventhandler


