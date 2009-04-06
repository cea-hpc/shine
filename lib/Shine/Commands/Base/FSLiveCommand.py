# FSLiveCommand.py -- Base commands class : live filesystem
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

"""
Base class for live filesystem commands (start, stop, status, etc.).
"""

from RemoteCommand import RemoteCommand, RemoteCriticalCommand

# Options support classes
from Support.Indexes import Indexes
from Support.FS import FS
from Support.Target import Target
from Support.Verbose import Verbose
from Support.Yes import Yes


class FSLiveCommand(RemoteCommand):
    """
    shine <cmd> [-f <fsname>] [-t <target>] [-i <index(es)>] [-n <nodes>] [-dqv]
    """
    
    def __init__(self):
        RemoteCommand.__init__(self)

        self.fs_support = FS(self, optional=True)
        self.target_support = Target(self)
        self.indexes_support = Indexes(self)
        self.verbose_support = Verbose(self)

class FSLiveCriticalCommand(FSLiveCommand):

    def __init__(self):
        FSLiveCommand.__init__(self)
        self.yes_support = Yes(self)

    def ask_confirm(self, prompt):
        """
        Ask user for confirmation if -y not specified.

        Return True when the user confirms the action, False otherwise.
        """
        return self.yes_support.has_yes() or FSLiveCommand.ask_confirm(self, prompt)

