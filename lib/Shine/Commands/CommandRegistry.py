# CommandRegistry.py -- Shine commands registry
# Copyright (C) 2007 CEA
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

# Base command class definition
from Base.Command import Command

# Import list of enabled commands (defined in the module __init__.py)
from Shine.Commands import commandList

# ----------------------------------------------------------------------
# Command Registry
# ----------------------------------------------------------------------


class CommandRegistry:
    """ Container object to deal with commands.
    """

    current = None

    def __init__(self):
        self.cmd_list = []
        self.cmd_dict = {}

        # Autoload commands
        self._load()

    def __len__(self):
        "Return the number of commands."
        return len(self.cmd_list)

    def __iter__(self):
        "Iterate over available commands."
        for cmd in self.cmd_list:
            yield cmd

    # Private methods

    def _load(self):
        for cmdobj in commandList:
            self.register(cmdobj())

    # Public methods

    def get(self, name):
        return self.cmd_dict[name]

    def register(self, cmd):
        "Register a new command."
        if not isinstance(cmd, Command):
            raise something   # FIXME

        self.cmd_list.append(cmd)
        self.cmd_dict[cmd.get_name()] = cmd

    def execute(self, name, args):
        try:
            CommandRegistry.current = self.get(name)
        except KeyError, e:
            raise CommandNotFoundError(cmd.get_name())

        # Parse
        CommandRegistry.current.parse(args)

        # Execute
        CommandRegistry.current.execute()

    def output(cls, *args, **kwargs):
        CommandRegistry.current.output(kwargs)
    output = classmethod(output)


