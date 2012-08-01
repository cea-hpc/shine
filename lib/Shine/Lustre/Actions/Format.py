# Format.py -- Lustre action class : format
# Copyright (C) 2007-2010 CEA
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

import re

from Shine.Configuration.Globals import Globals

from Shine.Lustre.Actions.Action import FSAction
# take care of cross-dependency
import Shine.Lustre.Target

class CommonFormat(FSAction):
    """
    Common class for Format and TuneFS action as they share a lot of common
    arguments.
    """

    def __init__(self, target, **kwargs):
        FSAction.__init__(self, target)

        # Hack to work aroung cross-dependcy with Target
        self.MGT_TYPE = Shine.Lustre.Target.MGT.TYPE
        self.MDT_TYPE = Shine.Lustre.Target.MDT.TYPE
        self.OST_TYPE = Shine.Lustre.Target.OST.TYPE

        self.stripecount = kwargs.get('stripecount')
        self.stripesize = kwargs.get('stripesize')
        self.format_params = kwargs.get('format_params')
        self.addopts = kwargs.get('addopts')

        # Quota
        if kwargs.get('quota', False):
            self.quota_type = kwargs['quota_type']
        else:
            self.quota_type = None

    def _mgsnids(self):
        """
        Prepare the argument list for mgsnode NID parameters.
        """
        params = []
        # MGS NIDs
        for nidlist in self.comp.fs.get_mgs_nids():
            params += [ '"--mgsnode=%s"' % ','.join(nidlist) ]
        return params

    def _prepare_cmd(self):

        command = []

        # --mgsnode and specific --param
        if self.comp.TYPE == self.MDT_TYPE:
            command += self._mgsnids()
            if self.stripecount:
                command.append('--param=lov.stripecount=%d' % self.stripecount)
            if self.stripesize:
                command.append('--param=lov.stripesize=%d' % self.stripesize)
            if self.quota_type is not None:
                if Globals().lustre_version_is_smaller('2'):
                    option = 'mdt.quota_type'
                else:
                    option = 'mdd.quota_type'
                command.append('"--param=%s=%s"' % (option, self.quota_type))

        elif self.comp.TYPE == self.OST_TYPE:
            command += self._mgsnids()
            if self.quota_type is not None:
                command.append('"--param=ost.quota_type=%s"' % self.quota_type)

        # --failnode: NID(s) of failover partner
        target_nids = self.comp.get_nids()
        for nidlist in target_nids[1:]:

            # if 'network' is specified, restrict the list of partner
            if self.comp.network and self.comp.TYPE in [self.MDT_TYPE, self.OST_TYPE]:

                # Parse network field
                match = re.match("^([a-z0-9]+?)(\d+)?$", self.comp.network)
                if not match:
                    raise ValueError("Unrecognized network: %s" %
                                     self.comp.network)
                suffix = ((match.group(1), match.group(2) or '0'))

                # Analyze NID list.
                def same_suffix(nid):
                    m = re.match(".*@([a-z0-9]+?)(\d+)?$", nid)
                    return (m and (m.group(1), m.group(2) or '0') == suffix)
                nidlist = [nid for nid in nidlist if same_suffix(nid)]

            # if there is still some matching partners, add them
            if len(nidlist) > 0:
                nids = ','.join(nidlist)
                command.append('"--failnode=%s"' % nids)

        # --network: restrict target to a specific LNET network
        if self.comp.network and self.comp.TYPE in [self.MDT_TYPE, self.OST_TYPE]:
            command.append('--network=%s' % self.comp.network)

        # Generic --param
        if self.format_params and self.format_params.get(self.comp.TYPE):
            command.append('"--param=%s"' %
                    self.format_params.get(self.comp.TYPE))

        # Mount options from command line
        if self.addopts:
            command.append(self.addopts)

        return command


class Tunefs(CommonFormat):
    """
    Run 'tunefs' command on Lustre devices.
    """

    NAME = 'tunefs'

    def __init__(self, target, **kwargs):
        CommonFormat.__init__(self, target, **kwargs)
        self.writeconf = kwargs.get('writeconf', False)

    def _prepare_cmd(self):
        """
        Prepare the 'tunefs' command line.
        """

        command = [ "tunefs.lustre --erase-params --quiet" ]

        command += CommonFormat._prepare_cmd(self)

        # Writeconf flag
        if self.writeconf:
            command.append('--writeconf')

        command.append(self.comp.dev)

        return command


class Format(CommonFormat):
    """
    File system format action class.
    """

    NAME = 'format'

    def __init__(self, target, **kwargs):
        CommonFormat.__init__(self, target, **kwargs)
        self.mkfs_options = kwargs.get('mkfs_options')

    def _prepare_cmd(self):
        """Return target format command line."""

        command = ['mkfs.lustre --reformat --quiet']
        command.append('"--fsname=%s"' % self.comp.fs.fs_name)

        if self.comp.TYPE == self.MGT_TYPE:
            # '--mgs' and not '--mgt'
            command.append("--mgs")

        elif self.comp.TYPE == self.MDT_TYPE:
            command.append("--mdt")
            command.append("--index=%d" % self.comp.index)

        elif self.comp.TYPE == self.OST_TYPE:
            command.append("--ost")
            command.append("--index=%d" % self.comp.index)

        command += CommonFormat._prepare_cmd(self)

        # --mkfsoptions
        mkfsopts = []
        if self.comp.journal:
            # Declare the external journal
            mkfsopts += ["-j -J device=%s" % self.comp.journal.dev]
        if self.mkfs_options and self.mkfs_options.get(self.comp.TYPE):
            mkfsopts.append(self.mkfs_options.get(self.comp.TYPE))
        if len(mkfsopts) > 0:
            command.append('"--mkfsoptions=%s"' % ' '.join(mkfsopts))

        # loop back devices
        if not self.comp.dev_isblk:
            command.append('--device-size=%d' % (self.comp.dev_size / 1024))

        command.append(self.comp.dev)

        return command

    def launch(self):
        """
        Create a command line and schedule it to be run by self.task

        If a journal device for this target exists, a dedicated action for it is
        first process before really doing the job for the full target.
        """

        # Format first the journal if it exists
        if self.comp.journal:
            self.comp.journal.format(nextaction=self)
            # It is ok to not launch current action here. In JournalFormat 
            # ev_close(), FSAction.launch(self) will be called to run
            # the normal launch method.
        else:
            FSAction.launch(self)


class JournalFormat(FSAction):
    """
    Specific Format Action for a journal device.

    This action should be associated with the target object and the format
    action of this target.
    """

    NAME = 'format'

    def __init__(self, comp, nextaction):
        FSAction.__init__(self, comp)
        self.nextaction = nextaction

    def _prepare_cmd(self):
        """Return target journal device format command line."""
        return [ "mke2fs -q -F -O journal_dev -b 4096 %s" % self.comp.dev ]

    def ev_close(self, worker):
        """Event callback when journal format ends."""
        FSAction.ev_close(self, worker)
        # action succeeded
        if worker.retcode() == 0:
            # Journal is done, launch next step
            # This is not pretty as we ignore the launch() method of nextaction.
            FSAction.launch(self.nextaction)
