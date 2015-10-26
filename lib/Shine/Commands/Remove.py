# Remove.py -- File system removing commands
# Copyright (C) 2007, 2008 BULL S.A.S
# Copyright (C) 2009-2015 CEA
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

"""
Shine 'remove' command classes.

The remove command aims to uninstall a Lustre filesystem setup with Shine.
This will interact with the backend and will remove local cached files.
"""

import sys

from Shine.Configuration.FileSystem import ModelFileIOError

from Shine.Commands.Base.FSLiveCommand import FSLiveCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_FAILURE

from Shine.Lustre.FileSystem import MOUNTED, RECOVERING, RUNTIME_ERROR

from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler


class Remove(FSLiveCommand):
    """
    This Remove Command object is used to completly remove the
    File System description from the Shine environment.
    All datas are lost after the Remove command completion.
    """

    NAME = "remove"
    DESCRIPTION = "Remove a previously installed file system"

    CRITICAL = True

    GLOBAL_EH = FSGlobalEventHandler

    def execute(self):

        # Option sanity check
        self.forbidden(self.options.model, "-m, use -f")

        try:
            return FSLiveCommand.execute(self)
        except ModelFileIOError:
            if self.has_local_flag():
                return 0
            raise

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        rc = RC_OK

        # Warn if trying to act on wrong nodes
        servers = fs.components.managed().servers()
        if not self.check_valid_list(fs.fs_name, servers, 'uninstall'):
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
                    self.display_proxy_errors(fs)
                    print "WARNING: Removing %s might failed on some nodes " \
                          "(see above)!" % fs.fs_name

            # Confirmation
            if not self.ask_confirm("Please confirm the removal of filesystem" \
                                    " ``%s''" % fs.fs_name):
                return RC_FAILURE

            # Do the job now!
            print "Removing filesystem %s..." % fs.fs_name
            if fs.remove(dryrun=self.options.dryrun):
                print "WARNING: failed to remove all filesystem %s " \
                      "configuration files" % fs.fs_name

            # XXX: This is not really nice. Need to find a better way.
            if not self.options.nodes \
               and not self.options.excludes \
               and not self.options.targets \
               and not self.options.labels \
               and not self.options.failover \
               and not self.options.indexes:

                print "Unregistering FS %s from backend..." % fs.fs_name
                if self.options.dryrun:
                    retcode = 0
                else:
                    retcode = self.unregister_fs(fs_conf)
                if retcode:
                    msg = "Error: failed to unregister FS from backend " \
                          "(rc = %d)" % retcode
                    print >> sys.stderr, msg
                    return RC_FAILURE

            print "Filesystem %s removed." % fs.fs_name

        # Local mode (either -R or -L)
        else:
            if fs.remove(dryrun=self.options.dryrun):
                if self.options.local:
                    msg = "Error: failed to remove filesystem ```%s'' " \
                          "configuration files" % fs.fs_name
                    print >> sys.stderr, msg
                return RC_FAILURE

            elif self.options.local:
                print "Filesystem %s removed." % fs.fs_name

        return rc

    def unregister_fs(self, fs_conf):
        """
        Unregister all client nodes and the filesystem from the backend.
        """
        fs_conf.unregister_targets()

        # Unregister file system configuration from the backend
        fs_conf.unregister_fs()
