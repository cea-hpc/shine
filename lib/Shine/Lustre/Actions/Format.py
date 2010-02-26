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

from Action import Action


class Format(Action):
    """
    File system format action class.
    """

    def __init__(self, target, **kwargs):
        Action.__init__(self)
        self.target = target
        assert self.target != None
        self.stripecount = kwargs.get('stripecount', 1)
        self.stripesize = kwargs.get('stripesize', 1048576)
        self.format_params = kwargs.get('format_params')
        self.mkfs_options = kwargs.get('mkfs_options')
        self.activate_quota = kwargs.get('quota', False)
        self.quota_type = kwargs.get('quota_type', "")
        self.mkfsopts = []
        self.jformat = False

    def launch(self):
        """
        Format file system target.
        """
        # Format journal device first if specified.
        if self.target.jdev:
            self.jformat = True
            self.mkfsopts = ["-j", "-J", "device=%s" % self.target.jdev]
            command = "export PATH=/usr/lib/lustre:$PATH; mke2fs -q -F -O journal_dev -b 4096 %s" % self.target.jdev
            self.task.shell(command, handler=self)
        else:
            self.launch_format()

    def launch_format(self):
        self.jformat = False
        
        command = ["export PATH=/usr/lib/lustre:$PATH;", "mkfs.lustre", "--reformat", '"--fsname=%s"' % \
                self.target.fs.fs_name]
        command.append("--quiet")

        mgs_nids = self.target.fs.get_mgs_nids()

        if self.target.type == 'mgt':

            command.append("--mgs")     # '--mgs' and not '--mgt'

        elif self.target.type == 'mdt':

            command.append("--mdt")

            # MGS NIDs (several MGS supported but only one NID per MGS supported for now)
            for nid in mgs_nids:
                command.append('"--mgsnode=%s"' %  nid)

            command.append("--index=%d" % self.target.index)

            if self.stripecount:
                command.append('"--param=lov.stripecount=%d"' % self.stripecount)
            if self.stripesize:
                command.append('"--param=lov.stripesize=%d"' % self.stripesize)

            if self.activate_quota:
                command.append('"--param=mdt.quota_type=%s"' % \
                        self.quota_type)

        elif self.target.type == 'ost':

            command.append("--ost")

            # MGS NIDs
            for nid in mgs_nids:
                command.append('"--mgsnode=%s"' %  nid)

            command.append("--index=%d" % self.target.index)

            if self.activate_quota:
                command.append('"--param=ost.quota_type=%s"' % \
                        self.quota_type)

        # failnode: NID(s) of failover partner
        target_nids = self.target.get_nids()
        if len(target_nids) > 1:
            for nid in target_nids[1:]:
                command.append('"--failnode=%s"' % nid)

        if self.mkfs_options:
            opts = self.mkfs_options.get(self.target.type)
            if opts:
                self.mkfsopts.append(opts)

        if len(self.mkfsopts) > 0:
            command.append('"--mkfsoptions=%s"' % ' '.join(self.mkfsopts))

        if self.format_params:
            param = self.format_params.get(self.target.type)
            if param:
                command.append('"--param=%s"' % param)

        # Loop devices handling
        if not self.target.dev_isblk:
            command.append('"--device-size=%d"' % (self.target.dev_size/1024))

        command.append(self.target.dev)

        self.task.shell(' '.join(command), handler=self)

    def ev_start(self, worker):
        if self.jformat:
            self.target.fs._invoke('ev_formatjournal_start', target=self.target)

    def ev_close(self, worker):
        if self.jformat:
            act = "formatjournal"
        else:
            act = "formattarget"

        if worker.did_timeout():
            # action timed out
            self.target._action_timeout(act)
        elif worker.retcode() == 0:
            # action succeeded
            self.target._action_done(act)
            if self.jformat:
                # Journal is done, go to next step...
                self.launch_format()
        else:
            # action failure
            self.target._action_failed(act, worker.retcode(), worker.read())

