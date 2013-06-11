# StopRouter.py -- Stop router
# Copyright (C) 2010-2012 CEA
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

"""Action class to handle router stop command and event handling."""

from Shine.Lustre.Actions.Action import FSAction, Result

class StopRouter(FSAction):
    """
    File system router (ie: stop lnet) stop class.
    """

    NAME = 'stop'

    def _already_done(self):
        """Return a Result object if the router is already stopped."""
        if self.comp.is_stopped():
            return Result('router is already disabled')
        else:
            return None

    def _prepare_cmd(self):
        """Stop LNET."""
        # XXX: Commands are joined with a simple ';' to workaround ab issue
        # when a target or a client is started on a router node.
        # All lustre modules will be loaded, and, when stopping, 
        # 'lctl net down' will cry, but it has done the required work.
        # So, lustre_rmmod is the final check to be sure the router is stopped.
        # This will be cleaned when a real module management will be done
        # directly by Shine.
        return [ "lctl net down", ";", "lustre_rmmod" ]
