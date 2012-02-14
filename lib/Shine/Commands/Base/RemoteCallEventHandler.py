# RemoteCallEventHandler.py -- Lustre remote call event handling (for -R)
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


from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.Actions.Proxy import SHINE_MSG_VERSION, SHINE_MSG_MAGIC

import binascii, pickle
import sys


class RemoteCallEventHandler(EventHandler):
    """
    Special shine EventHandler installed when called with -R (remote
    call), which aims to serialize all events instead of printing human
    output.
    """

    def _shine_msg_pack(self, **kwargs):
        """
        This is the shine event serialization method.
        """
        # To be more evolutive, Shine message contains only a dict.
        sys.stdout.write("%s%d:%s" % (SHINE_MSG_MAGIC, SHINE_MSG_VERSION,
                          binascii.b2a_base64(pickle.dumps(kwargs, -1))))
        sys.stdout.flush()

    def event_callback(self, compname, action, status, node, **kwargs):
        # For distant message, we do not need to send the node. It will
        # be extract from the incoming server name.
        self._shine_msg_pack(compname=compname, action=action,
                             status=status, **kwargs)
