# FileSystem.py -- Lustre FS base class
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

from MGS import MGS
from MDS import MDS
from OSS import OSS

from Shine.Utilities.Cluster.Task import Task
from Shine.Utilities.AsciiTable import AsciiTable

class FileSystem:

    def __init__(self, config):
        self.config = config
        self.fs_name = config.get_fs_name()
        
    def get_mgs_nid(self):
        #mgsdic = self.servers['mgs']
        mgt = self.targets['mgt'][0]
        return "%s@%s0" %  (list(mgt)[0], self.config.get_nettype())


    def test(self, target):

        task = Task.current()

       # cmd = "shine test -L -f testfs"

       # worker = task.worker(cmd, self.test_cb)
        
        for mgs in self.servers['mgs'].itervalues():
            mgs.test()
            break

        for mds in self.servers['mds'].itervalues():
            mds.test()
            break

        for oss in self.servers['oss'].itervalues():
            oss.test()

        task.run()

    def format(self, target):
        pass

    def start(self, target):
        pass
        
    def stop(self, target):
        pass

    def status(self):
        task = Task.current()

    def info(self):
        print "Filesystem %s:" % self.fs_name

        # XMF path
        print "%20s : %s" % ("Cfg path", self.config.get_cfg_filename())

        # Network type
        print "%20s : %s" % ("Network", self.config.get_nettype())

        # Quotas
        print "%20s : %s" % ("Quotas", self.config.get_quota())

        # Stripes
        print "%20s : size=%d, count=%d" % ("LOV stripping", self.config.get_stripesize(),
            self.config.get_stripecount())

        # Print FS user description
        print "%20s :" % "Description",
        ncols = AsciiTable.get_term_cols()
        margin = 22
        # Pretty print (with left margin) if possible
        if ncols > margin * 2:
            splited = self.config.get_description().split()
            sz = 0
            while len(splited) > 0:
                w = splited.pop(0)
                wsz = len(w) + 1
                sz += wsz
                if sz > ncols - margin:
                    print
                    print " " * margin,
                    sz = wsz
                print w,
        else:
            print " %s" % self.config.get_description()

        
        
