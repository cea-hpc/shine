# ProxyAction.py -- Abstract class for shine command proxy
# Copyright (C) 2007-2011 CEA
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


import os
import sys
import binascii, pickle

from ClusterShell.Task import task_self
from Shine.Lustre.Actions.Action import Action

# For V2 Compat
from Shine.Lustre.Actions.Action import ErrorResult

# SHINE PROXY PROTOCOL CONSTANTS
SHINE_MSG_MAGIC = "SHINE:"
SHINE_MSG_VERSION = 3

class ProxyActionUnpackError(Exception):
    """
    An error occured while trying to unpack a shine event message.
    """

class ProxyAction(Action):
    """
    Abstract shine proxy action class.
    """

    NAME = 'proxy'

    def __init__(self, task=task_self()):
        Action.__init__(self, task)
        self.progpath = os.path.abspath(sys.argv[0])

    def _shine_msg_unpack(self, msg):
        """
        Parse a raw string from a remote shine command.
        Return a dict containing the information put by
         RemoteCallEventHandler._shine_msg_pack()
        """
        # check for any shine msg
        if not msg.startswith("SHINE:"):
            raise ProxyActionUnpackError("Missing shine message prefix")

        # Identified shine msg of the form SHINE:<version>:<pickle>
        try:
            # unpack pickle object
            version, data = msg[6:].split(':', 1)
            if int(version) == SHINE_MSG_VERSION:
                return pickle.loads(binascii.a2b_base64(data))
            elif int(version) == 2:
                return self._shine_msg_unpack_v2(data)
            else:
                raise ProxyActionUnpackError("Shine message version mismatch")
        except Exception, exp:
            raise ProxyActionUnpackError("Unknown error: %s" % exp)

    @classmethod
    def _shine_msg_unpack_v2(cls, msg):
        """Compatibility function to unpack old-style v2 messages."""
        # v2 message looks like:
        # SHINE:2:ev_starttarget_done:{node:, comp:, rc:, message:}

        event, msg = msg.split(':', 1)
        data = pickle.loads(binascii.a2b_base64(msg))
        dummy, actioncomp, data['status'] = event.split('_', 3)
        for name in ('router', 'client', 'target', 'journal'):
            if actioncomp.endswith(name):
                data['action'] = actioncomp[:-len(name)]
                data['compname'] = name
                break

        # Result is only possible for 'failed' event in v2.
        if data['status'] == 'failed':
            data['result'] = ErrorResult(message=data.get('message'),
                                         retcode=data.get('rc'))
        return data
