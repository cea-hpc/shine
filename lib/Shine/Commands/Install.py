# Install.py -- File system installation commands
# Copyright (C) 2007-2013 CEA
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

from Shine.Configuration.Globals import Globals 

from Shine.FSUtils import create_lustrefs
from Shine.Lustre.FileSystem import FSRemoteError

from Shine.Commands.Base.Command import Command, CommandHelpException
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_FAILURE

# Lustre events
from Shine.Commands.Base.FSEventHandler import FSGlobalEventHandler


class Install(Command):
    """
    shine install -m /path/to/model.lmf
    """
 
    NAME = "install"
    DESCRIPTION = "Install a new file system."

    def execute(self):

        # Option sanity check
        self.forbidden(self.options.fsnames, "-f, see -m")
        self.forbidden(self.options.labels, "-l")
        self.forbidden(self.options.indexes, "-i")
        self.forbidden(self.options.failover, "-F")

        rc = RC_OK

        if not self.options.model:
            raise CommandHelpException("Lustre model file path"
                                   "(-m <model_file>) argument required.", self)

        eh = FSGlobalEventHandler(self)

        # Use this Shine.FSUtils convenience function.
        lmf = self.get_lmf_path()
        if lmf:
            print "Using Lustre model file %s" % lmf
        else:
            raise CommandHelpException("Lustre model file for ``%s'' not found:"
                        " please use filename or full LMF path.\n"
                        "Your default model files directory (lmf_dir) is: %s" %
                        (self.options.model, Globals().get_lmf_dir()), self)

        install_nodes = self.options.nodes
        excluded_nodes = self.options.excludes

        fs_conf, fs = create_lustrefs(self.get_lmf_path(),
                                      event_handler=eh, nodes=install_nodes,
                                      excluded=excluded_nodes)

        # Register the filesystem in backend
        print "Registering FS %s to backend..." % fs.fs_name
        if self.options.dryrun:
            rc = 0
        else:
            rc = self.register_fs(fs_conf)
        if rc:
            print "Error: failed to register FS to backend (rc=%d)" % rc
        else:
            print "Filesystem %s registered." % fs.fs_name

        # Helper message.
        # If user specified nodes which were not used, warn him about it.
        actual_nodes = fs.components.managed().servers()
        if not self.check_valid_list(fs_conf.get_fs_name(), \
                actual_nodes, "install"):
            return RC_FAILURE

        # Install file system configuration files; normally, this should
        # not be done by the Shine.Lustre.FileSystem object itself, but as
        # all proxy methods are currently handled by it, it is more
        # convenient this way...
        try:
            fs.install(fs_conf.get_cfg_filename(),
                       dryrun=self.options.dryrun)

            tuning_conf = Globals().get_tuning_file()
            if tuning_conf:
                fs.install(tuning_conf, dryrun=self.options.dryrun)

        except FSRemoteError, error:
            print "WARNING: Due to error, installation skipped on %s" \
                   % error.nodes
            rc = RC_FAILURE

        if not install_nodes and not excluded_nodes:
            # Give pointer to next user step.
            print "Use `shine format -f %s' to initialize the file system." % \
                    fs_conf.get_fs_name()

        return rc

    def register_fs(self, fs_conf):
        # register file system configuration to the backend
        fs_conf.register_fs()

        fs_conf.register_targets()
