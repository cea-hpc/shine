# Mount.py -- Mount file system clients
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
from Base.Support.MountPoint import MountPoint
from Base.Support.Node import Node
from Base.Support.Quiet import Quiet

import os
import sys

# ----------------------------------------------------------------------
# * shine mount
# ----------------------------------------------------------------------
class Mount(RemoteCommand):
    
    def __init__(self):
        RemoteCommand.__init__(self)

        # Command options
        self.fs_support = FS(self)
        self.mntpt_support = MountPoint(self)
        self.node_support = Node(self)
        self.quiet_support = Quiet(self)

    def get_name(self):
        return "mount"

    def get_desc(self):
        return "Mount file system client(s)."

    def execute(self):
        # for each selected file systems, get its config and mount it on nodes
        for fsname in self.fs_support.iter_fsname():
            conf = Configuration(fs_name=fsname)
            if self.local_flag or self.remote_call:
                fs = FSLocal(conf)
            else:
                fs = FSProxy(conf)

            fs.mount(self.node_support.get_nodes())

    def output(self, dic):
        if self.remote_call:
            self._print_pickle(dic)
        else:
            if dic['msg'] == "MOUNTING":
                if not self.quiet_support.has_quiet():
                    print "Mounting %s" % dic['fs']
            elif dic['msg'] == "RESULT":
                rc = dic['rc']
                if rc != 0:
                    print "Failed to mount %s on %s: %s" % (dic['fs'], dic['mntp'],
                           os.strerror(rc))
                    if dic.has_key('errbuf'):
                        print "%s" % dic['errbuf']
                    sys.exit(rc)
                elif not self.quiet_support.has_quiet():
                    print "Successfully mounted %s on %s" % (dic['fs'], dic['mntp'])

