# Server.py -- Lustre Server base class
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

from Shine.Configuration.Globals import Globals

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker

from Shine.Lustre.Target import Target



class Server(NodeSet):

    def __init__(self, nodename, fs):
        NodeSet.__init__(self, nodename)
        self.fs = fs
        self.targets = []
        self.target_class = None

    def spawn(self, cf_target):
        """
        Spawn a target.
        """
        # Create new server's target and add to the targets list
        self.targets.append(self.target_class(cf_target, self.fs))

    def test(self):
        """
        Test.
        """
        for target in self.targets:
            target.test()
        
    def start(self):
        """
        Start server's targets.
        """
        for target in self.targets:
            target.start()

    def stop(self):
        """
        Stop server's targets.
        """
        for target in self.targets:
            target.stop()

    def format(self):
        """
        Format server's targets.
        """
        for target in self.targets:
            target.format()

    def status(self):
        """
        Status of targets.
        """
        for target in self.targets:
            target.status()


