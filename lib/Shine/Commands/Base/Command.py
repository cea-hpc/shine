# Command.py -- Base command class
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

import binascii, pickle

# ----------------------------------------------------------------------
# Base Command Class and command class definitions
# ----------------------------------------------------------------------

class Command:
    """
    The base class for command objects that can be added to the commands
    registry.
    """
    def get_name(self):
        raise NotImplementedError("Derived classes must implement.")

    def get_params_desc(self):
        return ""

    def get_desc(self):
        return "Undocumented"

    def execute(self, args):
        raise NotImplementedError("Derived classes must implement.")

    #
    # Special output helper (pickling)
    #
    def _print_pickle(self, tpl):
        assert self.remote_call == True
        print binascii.b2a_base64(pickle.dumps(tpl, -1)), 

