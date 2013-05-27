# CommandPlugin.py -- Plugin command class
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


from Shine.Configuration.Exceptions import *
from Plugins import Plugin


class CommandPlugin(Plugin):
    """
    Plugin interface to add/modify shine command features.
    """
    def __init__(self):
        print "CommandPlugin:__init__"
        Plugin.__init__(self)
        self.cmd_list = []

    def get_name(self):
        raise NotImplementedError("Derived classes must implement.")

    def get_desc(self):
        return "Undocumented"

    def on_attach(self):
        print "attaching plugin %s for command %s" % (self.get_name(), self.cmd_name)


    # Command plugin specifics
    #
    def add_option(self, cmd_name):
        """ Add optional parameter
        """
        print "CommandPlugin:command_attach %s" % cmd_name
        self.cmd_list.append(cmd_name)

    def del_hook(self, cmd_name):
        """ Detach a command from this plugin
        """
        self.cmd_list.remove(cmd_name)
        



