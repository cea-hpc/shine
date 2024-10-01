# RemoteCallEventHandler.py -- Lustre remote call event handling (for -R)
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

import sys

from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.Actions.Proxy import shine_msg_pack

class RemoteCallEventHandler(EventHandler):
    """
    Special shine EventHandler installed when called with -R (remote
    call), which aims to serialize all events instead of printing human
    output.
    """

    def event_callback(self, evtype, **kwargs):
        """Convert each event it receives into an encoded line on stdout."""
        # For distant message, we do not need to send the node. It will
        # be extract from the incoming server name.
        if 'node' in kwargs:
            del kwargs['node']
        msg = shine_msg_pack(evtype=evtype, **kwargs)
        sys.stdout.write(msg.decode())
        sys.stdout.flush()
