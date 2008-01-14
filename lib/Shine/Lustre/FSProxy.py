# FSProxy.py -- Lustre FS proxy
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

from FileSystem import FileSystem
from MGS import MGS
from MDS import MDS
from OSS import OSS

from Actions.Action import *
from Actions.CreateDirs import CreateDirs
from Actions.Install import Install
from Actions.Proxies.Test import Test
from Actions.Proxies.Format import Format
from Actions.Proxies.Start import Start
from Actions.Proxies.Stop import Stop
from Actions.Proxies.Mount import Mount
from Actions.Proxies.Umount import Umount
from Actions.Proxies.Status import Status

from Shine.Utilities.Cluster.NodeSet import NodeSet
from Shine.Utilities.Cluster.Task import Task
from Shine.Utilities.Cluster.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable

import logging
import sys

class FSProxy(FileSystem):
    """
    File system proxy class. Redirect actions for local execution.
    """

    def __init__(self, config):
        FileSystem.__init__(self, config)

        # Get targets info from fs conf, and load NodeSets

        mgt = self.config.get_target_mgt()
        self.mgs = NodeSet(mgt.get_nodename())

        mdt = self.config.get_target_mdt()
        self.mds = NodeSet(mdt.get_nodename())

        self.oss = {}
        for ost in self.config.iter_targets_ost():
            self.oss.setdefault(ost.get_nodename(), NodeSet(ost.get_nodename()))

    def get_target_nodes(self, target=None):
        if not target:
            # It's easy with NodeSets
            nodes = self.mgs + self.mds
            for ost in self.oss:
                nodes += ost
            return nodes
        else:
            target = target.lower()
            if target == 'mgt':
                return self.mgs
            elif target == 'mdt':
                return self.mds
            elif target == 'ost':
                nodes = NodeSet()
                for ost in self.oss:
                    nodes += ost
                return nodes
            else:
                raise FSBadTargetError()
   
    def get_mgs_nid(self):
        #mgsdic = self.servers['mgs']
        mgt = self.targets['mgt'][0]
        return "%s@%s0" %  (list(mgt)[0], self.config.get_nettype())

    def install(self):
        """
        Install file system configuration on remote nodes.
        """
        try:
            action = CreateDirs(Task.current(), self)
            action.launch_and_run()

            action = Install(Task.current(), self)
            action.launch_and_run()

        except ActionErrorException, e:
            print e
            sys.exit(e.get_rc())

    def test(self, target=None):
        proxy = Test(Task.current(), self, target)
        proxy.launch_and_run()

    def format(self, target=None):
        """
        Proxy file system format command.
        """
        try:
            proxy = Format(Task.current(), self, target)
            proxy.launch_and_run()
        except ActionErrorException, e:
            print e
            sys.exit(e.get_rc())
        

    def start(self, target=None):
        """
        Proxy file system start command.
        """
        task = Task.current()

        if target:
            proxy = Start(task, self, target)
            proxy.launch_and_run()
        else:
            try:
                proxy = Start(task, self, 'mgt')
                proxy.launch_and_run()

                proxy = Start(task, self, 'ost')
                proxy.launch_and_run()

                proxy = Start(task, self, 'mdt')
                proxy.launch_and_run()
            except ActionErrorException, e:
                print e
                sys.exit(e.get_rc())
        
    def stop(self, target=None):
        """
        Proxy file system stop command.
        """
        task = Task.current()

        if target:
            proxy = Stop(task, self, target)
            proxy.launch_and_run()
        else:
            try:
                proxy = Stop(task, self, 'mdt')
                proxy.launch_and_run()

                proxy = Stop(task, self, 'ost')
                proxy.launch_and_run()

                proxy = Stop(task, self, 'mgt')
                proxy.launch_and_run()
            except ActionErrorException, e:
                print e
                sys.exit(e.get_rc())

    def status(self, target=None):
        proxy = Status(Task.current(), self, target)
        proxy.launch_and_run()

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

        
        
    def mount(self, nodes):
        """
        Proxy mount command.
        """
        try:
            action = CreateDirs(Task.current(), self, nodes)
            action.launch_and_run()

            action = Install(Task.current(), self, nodes)
            action.launch_and_run()

            proxy = Mount(Task.current(), self, NodeSet(nodes))
            proxy.launch_and_run()
        except ActionErrorException, e:
            print e
            sys.exit(e.get_rc())
        
    def umount(self, nodes):
        """
        Proxy umount command.
        """
        try:
            proxy = Umount(Task.current(), self, NodeSet(nodes))
            proxy.launch_and_run()
        except ActionErrorException, e:
            print e
            sys.exit(e.get_rc())
        
