# Command.py -- Base command class
# Copyright (C) 2007, 2008, 2009 CEA
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

from Support.Debug import Debug

from CommandRCDefs import *

import getopt


#
# Command exceptions are defined in Shine.Command.Exceptions
#

class Command(object):
    """
    The base class for command objects that can be added to the commands
    registry.
    """
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
    
    def get_name(self):
        raise NotImplementedError("Derived classes must implement.")

    def get_desc(self):
        return "Undocumented"

    def get_params_desc(self):
        pdesc = self.params_desc.strip()
        if self.has_subcommand():
            return "%s %s" % ('|'.join(self.get_subcommands()), pdesc)
        return pdesc

    def has_subcommand(self):
        """Return whether the command supports subcommand(s)."""
        return False

    def get_subcommands(self):
        """Return the list of subcommand(s)."""
        raise NotImplementedError("Derived classes must implement.")
    
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
        return i == 'y' or i == 'Y'


    def filter_rc(self, rc):
        """
        Allow derived classes to filter return codes.
        """
        # default is to not filter return code
        return rc

