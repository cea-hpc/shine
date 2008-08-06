# RemoteCommand.py -- Base command with remote capabilities
# Copyright (C) 2008 CEA
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

import binascii, pickle

class RemoteCommand(Command):
    
    def __init__(self):
        Command.__init__(self)
        self.remote_call = False
        self.local_flag = False
        attr = { 'optional' : True, 'hidden' : True }
        self.add_option('L', None, attr, cb=self.parse_L)
        self.add_option('R', None, attr, cb=self.parse_R)

    def parse_L(self, opt, arg):
        self.local_flag = True

    def parse_R(self, opt, arg):
        self.remote_call = True

    #
    # Special output helper (pickling)
    #
    def _print_pickle(self, tpl):
        assert self.remote_call == True
        print "SHINE:1:%s" % binascii.b2a_base64(pickle.dumps(tpl, -1)),

