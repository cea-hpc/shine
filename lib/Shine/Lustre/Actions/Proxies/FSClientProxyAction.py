# FSClientProxyAction.py -- Lustre generic FS client proxy action
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

from ClusterShell.NodeSet import NodeSet

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

from FSProxyAction import FSProxyAction


class FSClientProxyAction(FSProxyAction):
    """
    Generic file system client command proxy action class.
    """

    def __init__(self, fs, action, nodes, debug):
        FSProxyAction.__init__(self, fs, action, nodes, debug)
        self.fs = fs
        self.action = action
        assert isinstance(nodes, NodeSet)
        self.nodes = nodes
        self.debug = debug

        if self.fs.debug:
            print "FSClientProxyAction %s on %s" % (action, nodes)

    def launch(self):
        """
        Launch FS client proxy command.
        """
        command = ["%s" % self.progpath]
        command.append(self.action)
        command.append("-f %s" % self.fs.fs_name)
        command.append("-R")

        if self.debug:
            command.append("-d")

        # Schedule cluster command.
        self.task.shell(' '.join(command), nodes=self.nodes, handler=self)

