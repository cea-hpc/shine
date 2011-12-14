# Remove.py -- File system removing commands
# Copyright (C) 2007, 2008 BULL S.A.S
# Copyright (C) 2009 CEA
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
Shine 'remove' command classes.

The remove command aims to uninstall a Lustre filesystem setup with Shine.
This will interact with the backend and will remove local cached files.
"""

from Shine.Configuration.FileSystem import ModelFileIOError

from Shine.Commands.Base.FSLiveCommand import FSTargetLiveCriticalCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_FAILURE

from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, RUNTIME_ERROR


class Remove(FSTargetLiveCriticalCommand):
    """
    This Remove Command object is used to completly remove the
    File System description from the Shine environment.
    All datas are lost after the Remove command completion.
    """
 
    NAME = "remove"
    DESCRIPTION = "Remove a previously installed file system"

    def execute(self):
        try:
            return FSTargetLiveCriticalCommand.execute(self)
        except ModelFileIOError:
            if self.has_local_flag():
                return 0
            raise

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        rc = RC_OK

        # Warn if trying to act on wrong nodes
        servers = fs.components.managed().servers()
        if not self.nodes_support.check_valid_list(fs.fs_name, servers,
                                                   'uninstall'):
            return RC_FAILURE

        # Admin mode
        if not self.has_local_flag():

            # Get first the status of any FS components and display some
            # warnings if filesystem is not OK.
            fs.status()
            for state, targets in \
                fs.components.managed().groupby(attr='state'):

                # Mounted filesystem!
                if state in [MOUNTED, RECOVERING]:
                    labels = targets.labels()
                    print "WARNING: Some targets are started: %s" % labels
                # Error, won't be able to remove on these nodes
                elif state == RUNTIME_ERROR:
                    for nodes, msg in fs.proxy_errors:
                        print nodes
                        print '-' * 15
                        print msg
                    print "WARNING: Removing %s might failed on some nodes " \
                          "(see above)!" % fs.fs_name

            # Confirmation
            if not self.ask_confirm("Please confirm the removal of filesystem" \
                                    " ``%s''" % fs.fs_name):
                return RC_FAILURE

            # Do the job now!
            print "Removing filesystem %s..." % fs.fs_name
            if fs.remove():
                print "Error: failed to remove all filesystem %s " \
                      "configuration files" % fs.fs_name
                return RC_FAILURE

            # XXX: This is not really nice. Need to find a better way.
            if not self.nodes_support.get_nodeset() \
               and not self.nodes_support.get_excludes() \
               and not self.target_support.get_target() \
               and not self.label_support.get_labels() \
               and not self.target_support.get_failover() \
               and not self.indexes_support.get_rangeset():

                print "Unregistering FS %s from backend..." % fs.fs_name
                retcode = self.unregister_fs(fs_conf)
                if retcode:
                    print "Error: failed to unregister FS from backend " \
                          "(rc = %d)" % retcode
                    return RC_FAILURE

            print "Filesystem %s removed." % fs.fs_name

        # Local mode (either -R or -L)
        else:
            if fs.remove():
                if self.local_flag:
                    print "Error: failed to remove filesystem ```%s'' " \
                          "configuration files" % fs.fs_name
                return RC_FAILURE

            elif self.local_flag:
                print "Filesystem %s removed." % fs.fs_name
        
        return rc

    def unregister_fs(self, fs_conf):
        """
        Unregister all client nodes and the filesystem from the backend.
        """
        
        # Unregister all the file system client
        nodes = fs_conf.get_client_nodes()
        fs_conf.unregister_clients(nodes)

        fs_conf.unregister_targets()

        # Unregister file system configuration from the backend
        fs_conf.unregister_fs()
