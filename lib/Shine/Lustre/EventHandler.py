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


#EV_START=1


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
    
    def ev_formatjournal_start(self, node, target):
        pass

    def ev_formatjournal_done(self, node, target):
        pass

    def ev_formatjournal_failed(self, node, target, rc, message):
        pass

    def ev_formattarget_start(self, node, target):
        pass

    def ev_formattarget_done(self, node, target):
        pass

    def ev_formattarget_failed(self, node, target, rc, message):
        pass

    def ev_statustarget_start(self, node, target):
        """
        Target status request is starting on node.
        """

    def ev_statustarget_done(self, node, target):
        """
        Target status has been updated.
        """

    def ev_statustarget_failed(self, node, target, rc, message):
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

    def ev_statusclient_start(self, node, client):
        """
        Client status request is starting on node.
        """

    def ev_statusclient_done(self, node, client):
        """
        Client status has been updated.
        """

    def ev_statusclient_failed(self, node, client, rc, message):
        """
        A client status request has failed.
        """

    def ev_startclient_start(self, node, client):
        """
        A Lustre FS client is being started.
        """

    def ev_startclient_failed(self, node, client, rc, message):
        """
        A Lustre FS client has failed to start/mount.
        """

    def ev_startclient_done(self, node, client):
        """
        A Lustre FS client has started successfully.
        """

    def ev_stopclient_start(self, node, client):
        """
        A Lustre FS client is being stopped.
        """

    def ev_stopclient_failed(self, node, client, rc, message):
        """
        A Lustre FS client has failed to stop.
        """

    def ev_stopclient_done(self, node, client):
        """
        A Lustre FS client has been stopped successfully.
        """

