# Server.py -- Lustre Server base class
# Copyright (C) 2007, 2008, 2009 CEA
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

from Shine.Configuration.Globals import Globals

from ClusterShell.NodeSet import NodeSet

import socket


class Server(NodeSet):

    def __init__(self, node_name, nid):
        NodeSet.__init__(self, node_name)
        self.nid = nid

    def __str__(self):
        return "%s (%s)" % (NodeSet.__str__(self), self.nid)

    def is_local(self):
        local_hostname = socket.gethostname()
        local_hostname_short = local_hostname.split('.', 1)[0]
        assert len(self) == 1
        hostname = NodeSet.__str__(self)
        return local_hostname == hostname or \
                local_hostname_short == hostname


"""
class ServerLocal(Server):

    def start(self, targets):
        print "ServerLocal %s" % targets
        for target in targets:
            target.start()


class ServerDistant(Server):

    def start(self, targets):
        print "ServerDistant %s" % targets
        # distant start....
        
        proxy = Start()
        proxy.launch()

"""
