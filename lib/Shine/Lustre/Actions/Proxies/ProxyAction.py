# ProxyAction.py -- Abstract class for shine command proxy
# Copyright (C) 2007 CEA
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

from Shine.Lustre.Actions.Action import Action, ActionException
from ClusterShell.Task import task_self

import os
import sys

import binascii, pickle

# SHINE PROXY PROTOCOL CONSTANTS

SHINE_MSG_VERSION = 2


class ProxyActionException(ActionException):
    def __init__(self, nodes, message, rc=-1):
        ActionException.__init__(self, message, rc)
        self.nodes = nodes

class ProxyActionError(ProxyActionException):
    """
    Base class for proxy action error exceptions.
    """

class ProxyActionUnpackError(Exception):
    """
    An error occured while trying to unpack a shine event message.
    """

class ProxyAction(Action):
    """
    Astract shine proxy action class.
    """

    def __init__(self, task=task_self()):
        Action.__init__(self, task)
        self.progpath = os.path.abspath(sys.argv[0])

    def _shine_msg_unpack(self, msg):
        # check for any shine msg
        if not msg.startswith("SHINE:"):
            raise ProxyActionUnpackError("Missing shine message prefix")

        # Identified shine msg of the form SHINE:<version>:<event>:<pickle>
        try:
            # unpack event and pickle object
            version, event, data = msg[6:].split(':', 3)
            if int(version) != SHINE_MSG_VERSION:
                raise ProxyActionUnpackError("Shine message version mismatch")
            return event, pickle.loads(binascii.a2b_base64(data))
        except:
            raise ProxyActionUnpackError("Unknown error")

    def _shine_msg_unpack2(self, fs, node, buf):
        """
        Check and handle any shine file system event.
        """
        # check for any shine msg
        shine_msg = self._read_shine_msg(buf)
        if shine_msg is None:
            return False
        # unpack event and pickle object
        event, params = shine_msg
        # invoke file system event handler
        self.fs._invoke(event, node, **params)
        return True

