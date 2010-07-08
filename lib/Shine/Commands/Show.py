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
from Shine.Configuration.Exceptions import *

from Exceptions import *

# Command base class
from Base.Command import Command
from Base.CommandRCDefs import *
from Base.Support.FS import FS
from Base.Support.Verbose import Verbose
# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler

# Command helper
from Shine.FSUtils import open_lustrefs

from Shine.Utilities.AsciiTable import AsciiTable, AsciiTableLayout


class Show(Command):
    """
    shine show [-f <fsname>] <conf|fs|info|storage|tuning>
    """

    NAME = "show"
    DESCRIPTION = "Show configuration parameters."

    def __init__(self):
        Command.__init__(self)
        self.fs_support = FS(self, optional=True)
        self.verbose_support = Verbose(self, with_quiet=False)
        self.subcmd = None

    def has_subcommand(self):
        """The show command supports and even requires a subcommand."""
        return True

    def get_subcommands(self):
        return [ "conf", "fs", "info", "storage", "tuning" ]

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
                
                # Retrieve quota configuration information
                quota_info_string=''

                if fs_conf.has_quota():
                    quota_info_string += 'type=%s ' % fs_conf.get_quota_type()

                    qiunit_string = fs_conf.get_quota_iunit()
                    quota_info_string += 'iunit=%s ' %(qiunit_string or '[lustre_default]')

                    qbunit_string = fs_conf.get_quota_bunit()
                    quota_info_string += 'bunit=%s ' %(qbunit_string or '[lustre_default]')

                    qitune_string = fs_conf.get_quota_itune()
                    quota_info_string += 'itune=%s ' %(qitune_string or '[lustre_default]')

                    qbtune_string = fs_conf.get_quota_btune()
                    quota_info_string += 'btune=%s ' %(qbtune_string or '[lustre_default]')
                else:
                    quota_info_string = 'not activated'

                # Get file system stripping configuration information
                stripping_info_string = 'stripe_size=%s ' % fs_conf.get_stripesize()
                stripping_info_string += 'stripe_count=%s' % fs_conf.get_stripecount()

                # Get the device path used to mount the file system 
                # on client node
                device_path_string = fs_conf.get_nid(fs_conf.get_target_mgt().get_nodename()) \
                                    + ":/" + fs_conf.get_fs_name()

                # Add configuration parameter to the list of element displayed
                # in the summary tab.
                fslist.append(dict([['name', 'name'],
                                    ['value', fs_conf.get_fs_name()]]))
                fslist.append(dict([['name', 'mount path'],
                                    ['value', fs_conf.get_client_mount(None)]]))
                fslist.append(dict([['name', 'device path'],
                                    ['value', device_path_string]]))
                fslist.append(dict([['name', 'mount options'],
                                    ['value', fs_conf.get_mount_options()]]))
                fslist.append(dict([['name', 'quotas'],
                                    ['value', quota_info_string]]))
                fslist.append(dict([['name', 'stripping'],
                                    ['value', stripping_info_string]]))
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

            except:
                # We fail to get current file system configuration information.
                # Display an error message.
                print "Error with FS ``%s'' configuration files." % fsname
                raise

    def cmd_show_storage(self):
        """Show storage info"""
        from Shine.Configuration.Backend.BackendRegistry import BackendRegistry
        from Shine.Configuration.Backend.Backend import Backend

        backend = BackendRegistry().get_selected()
        if not backend:
            # no backend? check to be sure
            assert Globals().get_backend() == "None", \
                    "Error: please check your storage backend configuration" \
                    "(backend=%s)" % Globals().get_backend()
            print "Storage backend is disabled, please check storage information " \
                    "as a per-filesystem basis with ``show info''."
        else:
            backend.start() 
            cnt = 0
            for t in [ 'mgt', 'mdt', 'ost']:
                for dev in backend.get_target_devices(t):
                    print dev
                    cnt += 1
            print "Total: %d devices" % cnt
        return 0

    def cmd_show_tuning(self):
        """Show global tuning info"""
        print "Not implemented yet."

    def execute(self):
        result = 0

        if len(self.arguments) != 1:
            raise CommandHelpException("Invalid command usage.", self)

        self.subcmd = self.arguments[0]
        if self.subcmd not in self.get_subcommands():
            raise CommandHelpException("Cannot show this.", self)

        return getattr(self, 'cmd_show_%s' % self.subcmd)()
        
        




        for fsname in self.fs_support.iter_fsname():

            # Open configuration and instantiate a Lustre FS.
            fs_conf, fs = open_lustrefs(fsname, None,
                    nodes=None, indexes=None, event_handler=None)

            fs.set_debug(self.debug_support.has_debug())


        
        return result
