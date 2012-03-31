# Command.py -- Base command class
# Copyright (C) 2007, 2008, 2009, 2012 CEA
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


import getopt

from Shine.Lustre.Server import Server

from Shine.Commands.Base.CommandRCDefs import RC_FLAG_RUNTIME_ERROR
from Shine.Commands.Base.RemoteCallEventHandler import RemoteCallEventHandler
from Shine.Commands.Base.Support.Debug import Debug
from Shine.Commands.Base.Support.Nodes import Nodes
from Shine.Commands.Base.Support.Yes import Yes

#
# Command exceptions are defined in Shine.Command.Exceptions
#

class Command(object):
    """
    The base class for command objects that can be added to the commands
    registry.
    """

    NAME = "<undefined>"
    DESCRIPTION = "Undocumented"
    SUBCOMMANDS = None

    def __init__(self):
        self.options = {}
        self.getopt_string = ""
        self.params_desc = ""
        self.last_optional = 0
        self.arguments = None

        # All commands have debug support.
        self.debug_support = Debug(self)

    def is_hidden(self):
        """Return whether the command should not be displayed to user."""
        return False
    
    def get_params_desc(self):
        pdesc = self.params_desc.strip()
        if self.SUBCOMMANDS:
            return "%s %s" % ('|'.join(self.SUBCOMMANDS), pdesc)
        return pdesc

    def add_option(self, flag, arg, attr, cb=None):
        """
        Add an option for getopt with optional argument.
        """
        assert flag not in self.options

        optional = attr.get('optional', False)
        hidden = attr.get('hidden', False)

        if cb:
            self.options[flag] = cb

        object.__setattr__(self, "opt_%s" % flag, None)
            
        self.getopt_string += flag
        if optional:
            leftmark = '['
            rightmark = ']'
        else:
            leftmark = ''
            rightmark = ''

        if arg:
            self.getopt_string += ":"
            if not hidden:
                self.params_desc += "%s-%s <%s>%s " % (leftmark,
                    flag, arg, rightmark)
                self.last_optional = 0
        elif not hidden:
            if self.last_optional == 0:
                self.params_desc += "%s-%s%s " % (leftmark, flag, rightmark)
            else:
                self.params_desc = self.params_desc[:-2] + "%s%s " % (flag,
                    rightmark)
            
            if optional:
                self.last_optional = 1
            else:
                self.last_optional = 2

    def parse(self, args):
        """
        Parse command arguments.
        """
        options, arguments = getopt.gnu_getopt(args, self.getopt_string)
        self.arguments = arguments

        for opt, arg in options:
            trim_opt = opt[1:]
            callback = self.options.get(trim_opt)
            if callback:
                callback(trim_opt, arg)
            object.__setattr__(self, "opt_%s" % trim_opt, arg or True)

    def ask_confirm(self, prompt):
        """
        Ask user for confirmation.
        
        Return True when the user confirms the action, False otherwise.
        """
        i = raw_input("%s (y)es/(N)o: " % prompt)
        return i.lower() in ('y', 'yes')


    def filter_rc(self, rc):
        """
        Allow derived classes to filter return codes.
        """
        # default is to not filter return code
        return rc


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
            self.opt_n = Server.hostname_short()

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

    def ask_confirm(self, prompt):
        """
        Ask user for confirmation. Overrides Command.ask_confirm to
        avoid confirmation when called remotely (-R).

        Return True when the user confirms the action, False otherwise.
        """
        return self.remote_call or Command.ask_confirm(self, prompt)

    def filter_rc(self, rc):
        """
        When called remotely, return code are not used to handle shine action
        success or failure, nor for status info. To properly detect ssh or remote
        shine installation failures, we filter the return code here.
        """
        if self.remote_call:
            # Only errors of type RUNTIME ERROR are allowed to go up.
            rc &= RC_FLAG_RUNTIME_ERROR

        return Command.filter_rc(self, rc)

