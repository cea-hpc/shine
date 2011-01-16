# StartRouter.py -- Start router
# Copyright (C) 2010 CEA
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

"""Action class to handle router start command and event handling."""

from Shine.Lustre.Actions.Action import FSAction

class StartRouter(FSAction):
    """
    File system router (ie: start lnet) start class
    """

    NAME = 'start'

    def _prepare_cmd(self):
        """Start LNET which will start router if properly configured."""
        return [ "/sbin/modprobe lnet", "&&", "lctl net up" ]

