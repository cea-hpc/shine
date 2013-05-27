# Test.py -- Lustre action class : test
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
from Shine.Configuration.Configuration import Configuration

from Action import Action

from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.MGS import MGS
from Shine.Lustre.MDS import MDS
from Shine.Lustre.OSS import OSS

from Shine.Utilities.Cluster.NodeSet import NodeSet
from Shine.Utilities.Cluster.Event import EventHandler
from Shine.Utilities.Cluster.Task import Task
from Shine.Utilities.Cluster.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable

class Test(Action):
    """
    File system format action class.
    """

    def __init__(self, task, fs, target):
        Action.__init__(self, task)
        self.target = target

    def execute(self):
        """
        Proxy file system format command.
        """

        print "Test.execute()"

    def ev_close(self, worker):
        print "Test:ev_close_proxy"
        gdict = worker.gather_rc()
        for nodelist, rc in gdict.iteritems():
            print "rc = %d" % rc
        gdict = worker.gather()
        for nodelist, buf in gdict.iteritems():
            print "%s" % buf

    
