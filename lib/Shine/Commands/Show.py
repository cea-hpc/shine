# Show.py -- Show command
# Copyright (C) 2008, 2009 CEA
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

"""
Shine `show' command classes.

The show command aims to show various shine configuration parameters.
"""

# Configuration
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 

# Command base class
from Shine.Commands.Base.Command import Command
from Shine.Commands.Base.Support.FS import FS
from Shine.Commands.Base.Support.Verbose import Verbose
from Shine.Commands.Exceptions import CommandHelpException

# Utilities
from Shine.Utilities.AsciiTable import AsciiTable, AsciiTableLayout

from Shine.Configuration.Backend.BackendRegistry import BackendRegistry


class Show(Command):
    """
    shine show [-f <fsname>] [-v] <conf|fs|info|storage>
    """

    NAME = "show"
    DESCRIPTION = "Show configuration parameters."
    SUBCOMMANDS = [ "conf", "fs", "info", "storage" ]

    def __init__(self):
        Command.__init__(self)
        self.fs_support = FS(self, optional=True)
        self.verbose_support = Verbose(self, with_quiet=False)

    def cmd_show_conf(self):
        """Show shine.conf"""
        AsciiTable().print_from_simple_dict(Globals().get_dict())
        return 0
    
    def cmd_show_fs(self):
        """Show filesystems"""
        verb = self.verbose_support.has_verbose()
        fslist = []
        for fsname in self.fs_support.iter_fsname():
            try:
                fs_conf = Configuration(fsname)
            except:
                print "Error with FS ``%s'' configuration files." % fsname
                raise
            if not verb:
                print fs_conf.get_fs_name()
            else:
                fslist.append(dict([['FS name', fs_conf.get_fs_name()],
                    ['Description', fs_conf.get_description()]]))
        if verb:
            layout = AsciiTableLayout()
            layout.set_show_header(True)
            layout.set_column("FS name", 0, AsciiTableLayout.LEFT)
            layout.set_column("Description", 1, AsciiTableLayout.LEFT)
            AsciiTable().print_from_list_of_dict(fslist, layout)

        return 0

    def cmd_show_info(self):
        """Show filesystem info"""
        # Walk through the list of file system managed 
        # by the current node and specified by the user.
        for fsname in self.fs_support.iter_fsname():

            fslist = []
            try:
                # Get the file system configuration structure
                fs_conf = Configuration(fsname)
            except:
                # We fail to get current file system configuration information.
                # Display an error message.
                print "Error with FS ``%s'' configuration files." % fsname
                raise
                
            # Retrieve quota configuration information
            quota_info = ''
            if fs_conf.has_quota():
                quota_info += 'type=%s ' % fs_conf.get_quota_type()

                qiunit = fs_conf.get_quota_iunit() or '[lustre_default]'
                quota_info += 'iunit=%s ' % qiunit

                qbunit = fs_conf.get_quota_bunit() or '[lustre_default]'
                quota_info += 'bunit=%s ' % qbunit

                qitune = fs_conf.get_quota_itune() or '[lustre_default]'
                quota_info += 'itune=%s ' % qitune

                qbtune = fs_conf.get_quota_btune() or '[lustre_default]'
                quota_info += 'btune=%s ' % qbtune
            else:
                quota_info = 'not activated'

            # Get file system stripping configuration information
            stripping = 'stripe_size=%s ' % fs_conf.get_stripesize()
            stripping += 'stripe_count=%s' % fs_conf.get_stripecount()

            # Get the device path used to mount the file system 
            # on client node
            mgsnid = fs_conf.get_nid(fs_conf.get_target_mgt().get_nodename())
            device_path = "%s:/%s" % (mgsnid, fs_conf.get_fs_name())

            # Add configuration parameter to the list of element displayed
            # in the summary tab.
            fslist.append(dict([['name', 'name'],
                                ['value', fs_conf.get_fs_name()]]))
            fslist.append(dict([['name', 'default mount path'],
                                ['value', fs_conf.get_mount_path()]]))
            fslist.append(dict([['name', 'device path'],
                                ['value', device_path]]))
            fslist.append(dict([['name', 'mount options'],
                                ['value', fs_conf.get_mount_options()]]))
            fslist.append(dict([['name', 'quotas'],
                                ['value', quota_info]]))
            fslist.append(dict([['name', 'stripping'],
                                ['value', stripping]]))
            fslist.append(dict([['name', 'tuning'],
                                ['value', Globals().get_tuning_file()]]))
            fslist.append(dict([['name', 'description'],
                                ['value', fs_conf.get_description()]]))

            # Display the list of collected configuration information
            layout = AsciiTableLayout()
            layout.set_show_header(False)
            layout.set_column("name", 0, AsciiTableLayout.LEFT)
            layout.set_column("value", 1, AsciiTableLayout.LEFT)
            AsciiTable().print_from_list_of_dict(fslist, layout)


    def cmd_show_storage(self):
        """Show storage info"""

        backend = BackendRegistry().get_selected()
        if not backend:
            # no backend? check to be sure
            assert Globals().get_backend() == "None", \
                    "Error: please check your storage backend configuration" \
                    "(backend=%s)" % Globals().get_backend()
            print "Storage backend is disabled, please check storage " \
                  "information as a per-filesystem basis with ``show info''."
        else:
            backend.start() 
            cnt = 0
            for tgt in [ 'mgt', 'mdt', 'ost']:
                for dev in backend.get_target_devices(tgt):
                    print dev
                    cnt += 1
            print "Total: %d devices" % cnt
        return 0

    def execute(self):

        if len(self.arguments) != 1:
            raise CommandHelpException("Invalid command usage.", self)

        subcmd = self.arguments[0]
        if subcmd not in self.SUBCOMMANDS:
            raise CommandHelpException("Cannot show this.", self)

        return getattr(self, 'cmd_show_%s' % subcmd)()
