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

from Exceptions import *

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
            fs_conf, fs = create_lustrefs(self.lmf_support.get_lmf_path(),
                    event_handler=self)

            install_nodes = self.nodes_support.get_nodeset()
            excluded_nodes = self.nodes_support.get_excludes()

            # Install file system configuration files; normally, this should
            # not be done by the Shine.Lustre.FileSystem object itself, but as
            # all proxy methods are currently handled by it, it is more
            # convenient this way...
            actual_nodes = fs.install(fs_conf.get_cfg_filename(), 
                                      nodes=install_nodes, 
                                      excluded=excluded_nodes)

            # Helper message.
            # If user specified nodes which were not used, warn him about it.
            if not self.nodes_support.check_valid_list(fs_conf.get_fs_name(), \
                    actual_nodes, "install"):
                return RC_FAILURE

            # FIXME: Display a summary of what have been installed, even if
            # install_nodes was specified.
            if not install_nodes and not excluded_nodes:
                # Print short file system summary.
                print
                print "Lustre targets summary:"
                print "\t%d MGT on %s" % (fs.mgt_count, fs.mgt_servers)
                print "\t%d MDT on %s" % (fs.mdt_count, fs.mdt_servers)
                print "\t%d OST on %s" % (fs.ost_count, fs.ost_servers)
                print

                # Give pointer to next user step.
                print "Use `shine format -f %s' to initialize the file system." % \
                        fs_conf.get_fs_name()

            return RC_OK
