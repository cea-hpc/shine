# Router.py -- Shine Lustre Router
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

"""
Classes for Shine framework to manage Lustre LNET routers.
"""

import os 

from Shine.Lustre.Component import Component, ComponentError, \
                                   MOUNTED, OFFLINE, TARGET_ERROR, RUNTIME_ERROR

from Shine.Lustre.Actions.StartRouter import StartRouter
from Shine.Lustre.Actions.StopRouter import StopRouter

class Router(Component):
    """
    Manages a LNET router in Shine framework.
    """

    TYPE = 'router'
    DISPLAY_ORDER = 1
    START_ORDER = 1

    #
    # Text form for different router states. 
    #
    # Could be nearly merged with Target state_text_map if MOUNTED value
    # becomes the same.
    STATE_TEXT_MAP = { 
        None: "unknown",
        OFFLINE: "offline", 
        TARGET_ERROR: "ERROR", 
        MOUNTED: "online", 
        RUNTIME_ERROR: "CHECK FAILURE" 
    }

    def longtext(self):
        """
        Return the routeur server name.
        """
        return "router on %s" % self.server

    def lustre_check(self):
        """
        Check Router health at Lustre level.

        Check LNET routing capabilities and change object state
        based on the results.
        """

        # LNET is not loaded
        # Lustre 2.11+ moved lnet to sysfs, try both paths
        routesfile = '/sys/kernel/debug/lnet/routes'
        if not os.path.isfile(routesfile):
            routesfile='/proc/sys/lnet/routes'
            if not os.path.isfile(routesfile):
                self.state = OFFLINE
                return

        # Read routing information
        try:
            routes = open(routesfile)
            # read only first line
            state = routes.readline().strip().lower()
        except:
            self.state = RUNTIME_ERROR
            raise ComponentError(self, "Could not read routing information")

        # routing info tells this is ok?
        if state == "routing enabled":
            self.state = MOUNTED
        elif state == "routing disabled":
            self.state = TARGET_ERROR
            raise ComponentError(self, "Misconfigured router")
        else:
            self.state = RUNTIME_ERROR
            raise ComponentError(self, "Bad routing status")

    #
    # Client actions
    #

    def start(self, **kwargs):
        """Start a Lustre router."""
        return StartRouter(self, **kwargs)

    def stop(self, **kwargs):
        """Stop a Lustre router."""
        return StopRouter(self, **kwargs)
