# Status.py -- Check a component status
# Copyright (C) 2012 CEA
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

"""
This module contains the version of FSAction class to implement component
status checking.
"""

from Shine.Lustre.Actions.Action import FSAction, ACT_OK

class Status(FSAction):
    """
    Status action triggers component status checking.

    It does not run an external command.
    """

    NAME = 'status'

    def _shell(self):
        """
        No-op method. Status command does not need to run an external command.
        """
        self.set_status(ACT_OK)
        self.comp.action_done(self.NAME)
