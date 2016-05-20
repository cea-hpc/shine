# Execute.py -- Generic command execution
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
# $Id$

"""
This module contains the specific version of FSAction class to implement
Execute Action.
"""

from Shine.Lustre.Actions.Action import FSAction

class Execute(FSAction):
    """Generic command execution for any component."""

    NAME = 'execute'

    CHECK_MOUNTDATA = 'never'

    def _prepare_cmd(self):
        """
        There is no real preparation for Execute, as the command syntax is
        exactly the content of additional options (-o).
        """
        return [ self.addopts ]
