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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 

from Shine.FSUtils import create_lustrefs

from Base.Command import Command
from Base.CommandRCDefs import *
from Base.Support.LMF import LMF
from Base.Support.Nodes import Nodes


from ClusterShell.NodeSet import NodeSet

from Exceptions import *

from ClusterShell.NodeSet import NodeSet

class Install(Command):
    """
    shine install -m /path/to/model.lmf
    """
    
    def __init__(self):
        Command.__init__(self)

        self.lmf_support = LMF(self)
        self.nodes_support = Nodes(self)

    def get_name(self):
        return "install"

    def get_desc(self):
        return "Install a new file system."

    def execute(self):
        if not self.opt_m:
            raise CommandHelpException("Lustre model file path (-m <model_file>) " \
                    "argument required.", self)
        else:
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

            print "Registering FS %s to backend..." % fs.fs_name
            rc = self.register_fs(fs_conf)

            if rc:
                print "Error: failed to register FS to backend (rc=%d)" % rc
            else:
                print "Filesystem %s registered." % fs.fs_name

            # Install file system configuration files; normally, this should
            # not be done by the Shine.Lustre.FileSystem object itself, but as
            # all proxy methods are currently handled by it, it is more
            # convenient this way...
            fs.install(fs_conf.get_cfg_filename()) 

            # Helper message.
            # If user specified nodes which were not used, warn him about it.
            actual_nodes = fs.managed_target_servers() | fs.get_enabled_client_servers()
            if not self.nodes_support.check_valid_list(fs_conf.get_fs_name(), \
                    actual_nodes, "install"):
                return RC_FAILURE


            # Print short file system summary.
            print
            print "Install summary:"

            # Display enabled targets by display order (MGT, MDT, OST)
            for order, iter_targets in fs.managed_targets(group_attr="display_order"):
                target_list = list(iter_targets)
                # Get the target type in uppercase
                type = target_list[0].type.upper()
                # List of all servers for these targets
                servers = NodeSet.fromlist([ t.server for t in target_list ])
                print "\t%3d %3s on %s" % (len(target_list), type, servers)

            # Display enabled clients
            client_servers = fs.get_enabled_client_servers()
            if client_servers:
                print "\t%3d %3s on %s" % (len(client_servers), 'CLI', client_servers)

            print

            if not install_nodes and not excluded_nodes:
                # Give pointer to next user step.
                print "Use `shine format -f %s' to initialize the file system." % \
                        fs_conf.get_fs_name()

            # Notify backend of file system status mofication
            fs_conf.set_status_fs_installed()

            return RC_OK

    def register_fs(self, fs_conf):
        # register file system configuration to the backend
        fs_conf.register_fs()

        nodes = NodeSet()
        
        for node, path in fs_conf.iter_clients():
            nodes.add(node)
            
        # register all the file system client
        fs_conf.register_clients(nodes)
