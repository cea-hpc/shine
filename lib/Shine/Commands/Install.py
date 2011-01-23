# Install.py -- File system installation commands
# Copyright (C) 2007, 2008, 2009 CEA
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

from ClusterShell.NodeSet import NodeSet

from Shine.Configuration.Globals import Globals 

from Shine.FSUtils import create_lustrefs
from Shine.Lustre.FileSystem import FSRemoteError

from Shine.Commands.Base.Command import Command
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_FAILURE
from Shine.Commands.Base.Support.LMF import LMF
from Shine.Commands.Base.Support.Nodes import Nodes
from Shine.Commands.Exceptions import CommandHelpException



class Install(Command):
    """
    shine install -m /path/to/model.lmf
    """
 
    NAME = "install"
    DESCRIPTION = "Install a new file system."

    def __init__(self):
        Command.__init__(self)

        self.lmf_support = LMF(self)
        self.nodes_support = Nodes(self)

    def execute(self):

        rc = RC_OK

        if not self.opt_m:
            raise CommandHelpException("Lustre model file path (-m <model_file>) " \
                    "argument required.", self)

        # Use this Shine.FSUtils convenience function.
        lmf = self.lmf_support.get_lmf_path()
        if lmf:
            print "Using Lustre model file %s" % lmf
        else:
            raise CommandHelpException("Lustre model file for ``%s'' not found: " \
                    "please use filename or full LMF path.\n" \
                    "Your default model files directory (lmf_dir) " \
                    "is: %s" % (self.opt_m, Globals().get_lmf_dir()), self)

        install_nodes = self.nodes_support.get_nodeset()
        excluded_nodes = self.nodes_support.get_excludes()

        fs_conf, fs = create_lustrefs(self.lmf_support.get_lmf_path(),
                event_handler=self, nodes=install_nodes, 
                excluded=excluded_nodes)

        # Register the filesystem in backend
        print "Registering FS %s to backend..." % fs.fs_name
        rc = self.register_fs(fs_conf)
        if rc:
            print "Error: failed to register FS to backend (rc=%d)" % rc
        else:
            print "Filesystem %s registered." % fs.fs_name

        # Helper message.
        # If user specified nodes which were not used, warn him about it.
        actual_nodes = fs.components.managed().servers()
        if not self.nodes_support.check_valid_list(fs_conf.get_fs_name(), \
                actual_nodes, "install"):
            return RC_FAILURE

        # Install file system configuration files; normally, this should
        # not be done by the Shine.Lustre.FileSystem object itself, but as
        # all proxy methods are currently handled by it, it is more
        # convenient this way...
        try:
            fs.install(fs_conf.get_cfg_filename()) 
        except FSRemoteError, error:
            print "WARNING: Due to error, installation skipped on %s" \
                   % error.nodes
            rc = RC_FAILURE

        # Print short file system summary.
        if rc == RC_OK:
            print
            print "Install summary:"

            # Display enabled components by display order
            key = lambda t: (t.DISPLAY_ORDER, t.TYPE)
            for order, targets in fs.components.managed().groupby(key=key):
                # Get the target type in uppercase
                target_list = list(targets)
                type = target_list[0].TYPE.upper()[0:3]
                # List of all servers for these targets
                servers = targets.servers()
                print "\t%3d %3s on %s" % (len(targets), type, servers)

            print

        if not install_nodes and not excluded_nodes:
            # Give pointer to next user step.
            print "Use `shine format -f %s' to initialize the file system." % \
                    fs_conf.get_fs_name()

        # Notify backend of file system status mofication
        fs_conf.set_status_fs_installed()

        return rc

    def register_fs(self, fs_conf):
        # register file system configuration to the backend
        fs_conf.register_fs()

        nodes = NodeSet()
        
        for node, path in fs_conf.iter_clients():
            nodes.add(node)
            
        # register all the file system client
        fs_conf.register_clients(nodes)
