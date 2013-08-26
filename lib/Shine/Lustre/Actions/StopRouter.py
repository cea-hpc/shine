# StopRouter.py -- Stop router
# Copyright (C) 2010-2013 CEA
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
        # Depending on what was done before on the node (only router) or if some
        # targets or clients were also started, the only safe and simple way to
        # stop a router is to unload all modules.
        return [ "lustre_rmmod" ]
