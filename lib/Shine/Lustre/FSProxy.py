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

from FileSystem import FileSystem, FSBadTargetError
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

from Shine.Utilities.AsciiTable import AsciiTable, AsciiTableLayout

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker


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

    def get_target_nodes(self, target=None, flag_clients=False):
        if not target or target == "client":
            # It's easy with NodeSets
            nodes = self.mgs + self.mds
            for ost in self.oss:
                nodes += ost

            if flag_clients:
                nodes += self.config.get_client_nodes()

            return nodes
        else:
            ltarget = target.lower()
            if ltarget == 'mgt':
                return self.mgs
            elif ltarget == 'mdt':
                return self.mds
            elif ltarget == 'ost':
                nodes = NodeSet()
                for ost in self.oss:
                    nodes += ost
                return nodes
            else:
                raise FSBadTargetError(target)
   
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
                proxy_mgt = Start(task, self, 'mgt')
                proxy_mgt.launch_and_run()

                proxy_ost = Start(task, self, 'ost')
                proxy_ost.launch_and_run()

                proxy_mdt = Start(task, self, 'mdt')
                proxy_mdt.launch_and_run()

                # Print stop status in an ascii table
                tgt_list = proxy_mgt.get_tgt_list() + \
                    proxy_mdt.get_tgt_list() + \
                    proxy_ost.get_tgt_list()

                layout = AsciiTableLayout()

                layout.set_show_header(True)
                layout.set_column("target", 0, AsciiTableLayout.LEFT)
                layout.set_column("node", 1, AsciiTableLayout.CENTER)
                layout.set_column("dev", 2, AsciiTableLayout.LEFT)
                layout.set_column("status", 3, AsciiTableLayout.CENTER)

                AsciiTable().print_from_list_of_dict(tgt_list, layout)

            except Exception, e:
                print e
                raise
            except ActionErrorException, e:
                print e
                sys.exit(e.get_rc())
        
    def stop(self, target=None):
        """
        Proxy file system stop command.
        """
        task = Task.current()

        if target:
            proxy_target = Stop(task, self, target)
            proxy_target.launch_and_run()
        else:
            try:
                # Stop MDT first
                proxy_mdt = Stop(task, self, 'mdt')
                proxy_mdt.launch_and_run()

                # Stop OSTs
                proxy_ost = Stop(task, self, 'ost')
                proxy_ost.launch_and_run()

                # Stop MGT last
                proxy_mgt = Stop(task, self, 'mgt')
                proxy_mgt.launch_and_run()

                # Print stop status in an ascii table
                tgt_list = proxy_mgt.get_tgt_list() + \
                    proxy_mdt.get_tgt_list() + \
                    proxy_ost.get_tgt_list()

                layout = AsciiTableLayout()

                layout.set_show_header(True)
                layout.set_column("target", 0, AsciiTableLayout.LEFT)
                layout.set_column("node", 1, AsciiTableLayout.CENTER)
                layout.set_column("dev", 2, AsciiTableLayout.LEFT)
                layout.set_column("status", 3, AsciiTableLayout.CENTER)

                AsciiTable().print_from_list_of_dict(tgt_list, layout)

            except Exception, e:
                print e
                raise
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
        # if no nodes are specified, use config
        if not nodes:
            nodes = self.config.get_client_nodes()

        if len(nodes) == 0:
            print "Nothing to mount."
            return
        
        if self.debug:
            print "FSProxy mount nodes=%s" % nodes.as_ranges()
            
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
        if not nodes:
            nodes = self.config.get_client_nodes()

        try:
            proxy = Umount(Task.current(), self, NodeSet(nodes))
            proxy.launch_and_run()
        except ActionErrorException, e:
            print e
            sys.exit(e.get_rc())
        
    def mount_status(self, nodes):
        """
        Proxy mount status command.
        """
        pass
