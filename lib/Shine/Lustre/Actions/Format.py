# Format.py -- Lustre action class : format
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

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable

import sys

class Format(Action):
    """
    File system format action class.
    """

    def __init__(self, task, fs, target):
        Action.__init__(self, task)
        self.fs = fs
        self.target = target
        self.jformat = False
        self.mkfsoptions = ""
        assert self.target != None

    def launch(self):
        """
        Format file system target.
        """

        # Format journal device if specified
        if self.target.jdev:
            self.jformat = True

            self.mkfsoptions = '"--mkfsoptions=-j -J device=%s"' % self.target.jdev

            cmd = "mke2fs -q -O journal_dev -b 4096 %s" % self.target.jdev
            self.task.shell(cmd, handler=self)
        else:
            self.launch_format()

    def launch_format(self):
        self.jformat = False
        
        # Set flag for quota activation
        activate_quota = False
        
        # Do we need to add some parameters to activate quota on startup ?
        if self.fs.config.get_quota() == "yes":
            
            # Set flag to activate quota
            activate_quota  =True
            
            # Yes it is. Now retrieve quota configuration informations.
            quota_options_string = self.fs.config.get_quota_options()
            
            # Map the quota configuration information in a dictionary
            quota_options_dict = dict([list(x.strip().split('=')) \
                    for x in quota_options_string.split(',')])
        
        if self.target.target_name == "MGS":
            # '--index' only valid for MDT,OST
            # '--mgs' and not '--mgt'
            cmd = "mkfs.lustre --mgs --fsname=\"%s\" --reformat %s %s" % \
                    (self.fs.fs_name, self.mkfsoptions, self.target.dev)

        elif self.target.target_name == "MDT":
            
            # Do we need to add some parameters to activate quota on startup ?
            if activate_quota :
                
                self.mkfsoptions += "--param='mdt.quota_type=%s' " % \
                        quota_options_dict['quotaon']
            
            cmd = "mkfs.lustre --mdt --fsname=\"%s\" --mgsnode=%s --index=%d --reformat" \
                    % (self.fs.fs_name, self.fs.get_mgs_nid(), self.target.index)

            p_stripecount = self.fs.config.get_stripecount()
            if p_stripecount:
                cmd += " --param='lov.stripecount=%d'" % p_stripecount

            p_stripesize = self.fs.config.get_stripesize()
            if p_stripesize:
                cmd += " --param='lov.stripesize=%d'" % p_stripesize

            cmd += " %s %s" % (self.mkfsoptions, self.target.dev)

        elif self.target.target_name == "OST":
            
            # Do we need to add some parameters to activate quota on startup ?
            if activate_quota:
                
                self.mkfsoptions += "--param='ost.quota_type=%s' " \
                        % quota_options_dict['quotaon']

            cmd = "mkfs.lustre --ost --fsname=\"%s\" --mgsnode=%s --reformat %s %s" \
                    % (self.fs.fs_name, self.fs.get_mgs_nid(), self.mkfsoptions, \
                    self.target.dev)

        #cmd = "sleep 4"
        self.task.shell(cmd, handler=self)


    def ev_start(self, worker):
        if self.jformat:
            print "Formatting %s %s journal (%s)" % (self.target.target_name, \
                    self.target.get_id(), self.target.jdev)
        else:
            print "Formatting %s %s (%s)" % (self.target.target_name, \
                    self.target.get_id(), self.target.dev)

        sys.stdout.flush()

    def ev_close(self, worker):
        rc = worker.retcode()
        if self.jformat:
            if rc != 0:
                print "Formatting of %s %s journal (%s) failed with error %d" \
                        %(self.target.target_name, self.target.get_id(), \
                        self.target.jdev, rc)
                print worker.read()
            else:
                print "Formatting of %s %s journal (%s) succeeded" \
                        %(self.target.target_name, self.target.get_id(), \
                        self.target.jdev)
                self.launch_format()
        else:
            if rc != 0:
                print "Formatting of %s %s (%s) failed with error %d" \
                        %(self.target.target_name, self.target.get_id(), \
                        self.target.dev, rc)
                print worker.read()
            else:
                print "Formatting of %s %s (%s) succeeded" \
                        %(self.target.target_name, self.target.get_id(), \
                        self.target.dev)

        sys.stdout.flush()

