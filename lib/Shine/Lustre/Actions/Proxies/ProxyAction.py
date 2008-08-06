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

from Shine.Lustre.Actions.Action import Action

import os
import sys

import binascii, pickle

class ProxyAction(Action):
    """
    Astract shine proxy action class.
    """

    def __init__(self, task):
        Action.__init__(self, task)
        self.progpath = os.path.abspath(sys.argv[0])

    def _read_shine_msg(self, msg):
        if msg.startswith("SHINE:"):
            # Identified shine msg of the form SHINE:<version>:<pickle>
            try:
                version, info = msg[6:].split(':', 2)
                return pickle.loads(binascii.a2b_base64(info))
            except:
                print "read_shine_msg failure"
                raise
        return None


