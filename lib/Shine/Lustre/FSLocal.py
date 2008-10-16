# FSLocal.py -- Lustre FS
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

from Actions.Test import Test
from Actions.Format import Format
from Actions.Mount import Mount
from Actions.Umount import Umount

from FileSystem import FileSystem
from Target import TargetException
from MGS import MGS
from MDS import MDS
from OSS import OSS
from Client import Client

from Shine.Utilities.AsciiTable import AsciiTable
from ClusterShell.Task import *

import socket

class FSLocal(FileSystem):

    def __init__(self, config):
        FileSystem.__init__(self, config)
        self.config = config
        self.fs_name = config.get_fs_name()
        self.actions = []
        self.servers = {}
        self.hostname = socket.gethostname()
        self.short_hostname = self.hostname.split('.', 1)[0]
        #print "hostname %s short %s" % (self.hostname, self.short_hostname)
        
        # Get targets info from fs conf, and spawn Lustre servers and targets.
        mgt = self.config.get_target_mgt()
        self.mgs_nn = mgt.get_nodename()
        if self.check_nodename(mgt.get_nodename()):
            self.mgs = MGS(mgt.get_nodename(), self)
            self.mgs.spawn(mgt)
        else:
            self.mgs = None

        mdt = self.config.get_target_mdt()
        if self.check_nodename(mdt.get_nodename()):
            self.mds = MDS(mdt.get_nodename(), self)
            self.mds.spawn(mdt)
        else:
            self.mds = None

        self.oss = None
        for ost in self.config.iter_targets_ost():
            if self.check_nodename(ost.get_nodename()):
                if not self.oss:
                    self.oss = OSS(ost.get_nodename(), self)
                self.oss.spawn(ost)

        client_nodes = self.config.get_client_nodes()

        self.client = None
        for host in self.short_hostname, self.hostname:
            if client_nodes.intersection_update(host):
                assert len(client_nodes) == 1
                mntp = self.config.get_client_mount(client_nodes)
                self.client = Client(client_nodes.first(), mntp, self)
                break


    def check_nodename(self, name):
        #### name == socket.getfqdn()
        return name == self.short_hostname or name == self.hostname
        
    def push_action(self, action):
        action.launch()
        self.actions.append(action)
        if len(self.actions) > 999:
            self.process_actions()

    def process_actions(self):
        task_self().resume()
        self.actions = []

    def test(self, target):

        if (not target or target == 'mgt') and self.mgs:
            self.mgs.test()
        if (not target or target == 'mdt') and self.mds:
            self.mds.test()
        if not target or target == 'ost' and self.oss:
            self.oss.test()

        self.process_actions()

    def format(self, target=None):
    
        if (not target or target == 'mgt') and self.mgs:
            self.mgs.format()
        if (not target or target == 'mdt') and self.mds:
            self.mds.format()
        if (not target or target == 'ost') and self.oss:
            self.oss.format()

        self.process_actions()

    def start(self, target=None):

        if (not target or target == 'mgt') and self.mgs:
            self.mgs.start()
            self.process_actions()
        if (not target or target == 'ost') and self.oss:
            self.oss.start()
            self.process_actions()
        if (not target or target == 'mdt') and self.mds:
            self.mds.start()
            self.process_actions()
        
    def stop(self, target=None):
        if (not target or target == 'mdt') and self.mds:
            self.mds.stop()
            self.process_actions()
        if (not target or target == 'ost')  and self.oss:
            self.oss.stop()
            self.process_actions()
        if (not target or target == 'mgt') and self.mgs:
            self.mgs.stop()
            self.process_actions()
        
    def status(self, target=None):
        # XXX improve me with a list

        if (not target or target == 'mgt') and self.mgs:
            try:
                self.mgs.status()
            except TargetException, e:
                print e

        if (not target or target == 'mdt') and self.mds:
            try:
                self.mds.status()
            except TargetException, e:
                print e

        if (not target or target == 'ost') and self.oss:
            try:
                self.oss.status()
            except TargetException, e:
                print e

        if (not target or target=='client') and self.client:
            try:
                self.client.status()
            except TargetException, e:
                print e


    def info(self):
        pass
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

    def mount(self, nodes=None):
        #if self.debug:
        #    print "FSProxy mount %s"  % nodes.as_ranges()
        action = Mount(task_self(), self, target=None)
        action.launch_and_run()

    def umount(self, nodes=None):
        action = Umount(task_self(), self, target=None)
        action.launch_and_run()

        

