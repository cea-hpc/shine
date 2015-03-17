# EventHandler.py -- Lustre event handling
# Copyright (C) 2009-2015 CEA
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

__all__ = ['EventHandler']

#
# Duplicate this method here to avoid cyclic import loop with
# Shine.Lustre.Server
#
import socket
_CACHE_HOSTNAME_SHORT = None
def hostname_short():
    """Return cached short host name.

    If not already cached, resolve and cache it.
    """
    global _CACHE_HOSTNAME_SHORT
    if _CACHE_HOSTNAME_SHORT is None:
        _CACHE_HOSTNAME_SHORT = socket.getfqdn().split('.', 1)[0]
    return _CACHE_HOSTNAME_SHORT


class EventHandler(object):
    """
    Base class EventHandler. Event-based applications using the Shine library
    should override this class and handle events of their choice.
    """

    def local_event(self, evtype, **kwargs):
        """Raise an event, automatically providing local node information."""
        self.event_callback(evtype, node=hostname_short(), **kwargs)

    def event_callback(self, evtype, **kwargs):
        """
        Base event handler. It is called for each event received.

        This event handler could be overload to implement your own event
        management.
        """
        raise NotImplementedError
