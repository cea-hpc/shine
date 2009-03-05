# RemoteCallEventHandler.py -- Lustre remote call event handling (for -R)
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


from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.Actions.Proxies.ProxyAction import SHINE_MSG_VERSION

import binascii, pickle
import sys


class RemoteCallEventHandler(EventHandler):
    """
    Special shine EventHandler installed when called with -R (remote
    call), which aims to serialize all events instead of printing human
    output.
    """

    def _shine_pickle(self, **kwargs):
        """
        This is the shine event serialization method.
        """
        # event name is caller name
        event = sys._getframe(1).f_code.co_name
        sys.stdout.write("SHINE:%d:%s:%s" % (SHINE_MSG_VERSION, event,
                binascii.b2a_base64(pickle.dumps(kwargs, -1))))
        sys.stdout.flush()

    def ev_format_journal_start(self, node, target):
        self._shine_pickle(target=target)

    def ev_format_journal_done(self, node, target):
        self._shine_pickle(target=target)

    def ev_format_journal_failed(self, node, target, rc, message):
        self._shine_pickle(target=target, rc=rc, message=message)

    def ev_format_start(self, node, target):
        self._shine_pickle(target=target)

    def ev_format_done(self, node, target):
        self._shine_pickle(target=target)

    def ev_format_failed(self, node, target, rc, message):
        self._shine_pickle(target=target, rc=rc, message=message)

    def ev_statustarget_start(self, node, target):
        self._shine_pickle(target=target)

    def ev_statustarget_done(self, node, target):
        self._shine_pickle(target=target)

    def ev_statustarget_failed(self, node, target, rc, message):
        self._shine_pickle(target=target, rc=rc, message=message)

    def ev_starttarget_start(self, node, target):
        self._shine_pickle(target=target)

    def ev_starttarget_done(self, node, target):
        self._shine_pickle(target=target)

    def ev_starttarget_failed(self, node, target, rc, message):
        self._shine_pickle(target=target, rc=rc, message=message)

    def ev_stoptarget_start(self, node, target):
        self._shine_pickle(target=target)

    def ev_stoptarget_done(self, node, target):
        self._shine_pickle(target=target)

    def ev_stoptarget_failed(self, node, target, rc, message):
        self._shine_pickle(target=target, rc=rc, message=message)

    def ev_statusclient_start(self, node, client):
        self._shine_pickle(client=client)

    def ev_statusclient_done(self, node, client):
        self._shine_pickle(client=client)

    def ev_statusclient_failed(self, node, client, rc, message):
        self._shine_pickle(client=client, rc=rc, message=message)

    def ev_startclient_start(self, node, client):
        self._shine_pickle(client=client)

    def ev_startclient_done(self, node, client):
        self._shine_pickle(client=client)

    def ev_startclient_failed(self, node, client, rc, message):
        self._shine_pickle(client=client, rc=rc, message=message)

    def ev_stopclient_start(self, node, client):
        self._shine_pickle(client=client)

    def ev_stopclient_done(self, node, client):
        self._shine_pickle(client=client)

    def ev_stopclient_failed(self, node, client, rc, message):
        self._shine_pickle(client=client, rc=rc, message=message)

