# EventHandler.py -- Lustre event handling
# Copyright (C) 2009-2011 CEA
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



class EventHandler(object):
    """
    Base class EventHandler. Event-based applications using the Shine library
    should override this class and handle events of their choice.
    """

    def event_callback(self, compname, action, status, **kwargs):
        """
        Base event handler. It is called for each event received.

        This event handler could be overload to implement your own event
        management.
        """
        raise NotImplementedError
