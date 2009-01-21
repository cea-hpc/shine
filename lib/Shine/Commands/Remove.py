# Remove.py -- File system removing commands
# Copyright (C) 2007, 2008 BULL S.A.S
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

# Import Section

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals
from Shine.Configuration.Exceptions import *

from Shine.Lustre.FSLocal import FSLocal
from Shine.Lustre.FSProxy import FSProxy

from Base.RemoteCommand import RemoteCommand
from Base.Support.FS import FS

import getopt
import socket
import binascii
import pickle

# ----------------------------------------------------------------------
# * shine remove
# ----------------------------------------------------------------------
class Remove(RemoteCommand):
    """
    This Remove Command object is used to completly
    remove the File System description from the Shine
    environment.
    All datas are lost after the Remove command completion.
    """
    
    def __init__(self):
        """
        Initialization of the Remove command object
        """
        # Call parent intialization function
        RemoteCommand.__init__(self)

        self.fs_support = FS(self, optional=False)

    def get_name(self):
        """
        Return the name of the command.
        """
        return "remove"

    def get_desc(self):
        """
        Return the description message of the command.
        """
        return "Remove a previously installed file system"

    def execute(self):
        if not self.opt_f:
            # -f Option must be specified for this command
            print "Missing -f option. You must specify at least one file system name"
        else:
            # Walk through the list of File system name provided
            # by the user
            for fsname in self.fs_support.iter_fsname():
                try:
                    # Retrieve the file system configuration linked to this fsname
                    conf = Configuration(fs_name=fsname)

                    # FIXME : Check that the configuration is valid

                    # Where is running the command ?
                    if self.local_flag or self.remote_call:
                        # This code is executed on the remote nodes involved
                        # in the considered file systems

                        # On the local node
                        fs = FSLocal(conf)
                    else:
                        # This code is executed to the node where the user
                        # has launched the shine command
                        
                        # Rebuild file system object from it's configuration
                        fs = FSProxy(conf)

                    # Remove the File system
                    fs.remove()
                    
                except IOError, e:
                    print "Error: filesystem %s is not installed" % fsname

    def output(self, dic):
        """
        Function in charge of command output. The output depends
        on type of execution : on local node, on remote node.
        """
        # Am i running on local or remote node
        if self.remote_call:
            # This code is executed on the remote nodes involved
            # in the considered file systems

            # Output function for remote node instance.
            # Use pickle here
            self._print_pickle(dic)
        else:
            # This code is executed to the node where the user
            # has launched the shine command

            # Output code for local node instance.
            print "%s" % dic
