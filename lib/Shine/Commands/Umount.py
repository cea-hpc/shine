# Umount.py -- Unmount file system clients
# Copyright (C) 2007, 2008 CEA
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

from Shine.Lustre.FSLocal import FSLocal
from Shine.Lustre.FSProxy import FSProxy

from Base.RemoteCommand import RemoteCommand
from Base.Support.FS import FS
from Base.Support.Node import Node


# ----------------------------------------------------------------------
# * shine umount
# ----------------------------------------------------------------------
class Umount(RemoteCommand):

    def __init__(self):
        RemoteCommand.__init__(self)
        
        # the umount command supports -f and -n
        self.fs_support = FS(self)
        self.node_support = Node(self)

    def get_name(self):
        return "umount"

    def get_desc(self):
        return "Unmount file system client(s)."

    def execute(self):
        # for each selected file systems, get its config and unmount it on nodes
        for fsname in self.fs_support.iter_fsname():
            conf = Configuration(fs_name=fsname)
            if self.local_flag or self.remote_call:
                fs = FSLocal(conf)
            else:
                fs = FSProxy(conf)
            fs.umount(self.node_support.get_nodes())

    def output(self, dic):
        if self.remote_call:
            self._print_pickle(dic)
        else:
            print "Unmounting %s" % dic['fs']


    
