# EventHandler.py -- Lustre event handling
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


EV_START=1


class EventHandler(object):
    """
    Base class EventHandler. Event-based applications using the Shine library
    should override this class and handle events of their choice.
    """

    def __init__(self):
        pass

    def ev_preinstall_start(self, node):
        pass

    def ev_preinstall_done(self, node):
        pass
    
    def ev_preinstall_failed(self, node, rc, message):
        pass

    def ev_format_journal_start(self, node, target):
        pass

    def ev_format_journal_done(self, node, target):
        pass

    def ev_format_journal_failed(self, node, target, rc, message):
        pass

    def ev_format_start(self, node, target):
        pass

    def ev_format_done(self, node, target):
        pass

    def ev_format_failed(self, node, target, rc, message):
        pass

    def ev_status_start(self, node, target):
        """
        Target status request is starting on node.
        """

    def ev_status_done(self, node, target):
        """
        Target status has been updated.
        """

    def ev_status_failed(self, node, target, rc, message):
        """
        A target status request has failed.
        """

    def ev_starttarget_start(self, node, target):
        """
        A Lustre target is being started.
        """

    def ev_starttarget_failed(self, node, target, rc, message):
        """
        A Lustre target has failed to start.
        """

    def ev_starttarget_done(self, node, target):
        """
        A Lustre target has started successfully.
        """

    def ev_stoptarget_start(self, node, target):
        """
        A Lustre target is being stopped.
        """

    def ev_stoptarget_failed(self, node, target, rc, message):
        """
        A Lustre target has failed to stop.
        """

    def ev_stoptarget_done(self, node, target):
        """
        A Lustre target has been stopped successfully.
        """

    def evt_target(self, kind, target):
        pass


    def evt_client(self, kind, client):
        pass

