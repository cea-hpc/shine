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

    def ev_formatjournal_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_formatjournal_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_formatjournal_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_formattarget_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_formattarget_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_formattarget_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_fscktarget_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_fscktarget_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_fscktarget_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_statustarget_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_statustarget_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_statustarget_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_starttarget_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_starttarget_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_starttarget_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_stoptarget_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_stoptarget_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_stoptarget_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_tunefstarget_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_tunefstarget_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_tunefstarget_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_statusclient_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_statusclient_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_statusclient_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_mountclient_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_mountclient_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_mountclient_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_umountclient_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_umountclient_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_umountclient_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_statusrouter_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_statusrouter_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_statusrouter_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_startrouter_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_startrouter_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_startrouter_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)

    def ev_stoprouter_start(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_stoprouter_done(self, node, comp):
        self._shine_pickle(comp=comp)

    def ev_stoprouter_failed(self, node, comp, rc, message):
        self._shine_pickle(comp=comp, rc=rc, message=message)
