# Remove.py -- Lustre proxy action class : start
# Copyright (C) 2007 BULL
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

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

from Shine.Lustre.Actions.Action import ActionFailedError
from ProxyAction import ProxyAction

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable

import binascii
import pickle


class Remove(ProxyAction):
    """
    File system remove proxy action class.
    """

    def __init__(self, task, fs, nodes):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.nodes = nodes

    def launch(self):
        """
        Proxy file system remove command to target.
        """

        # Prepare proxy command
        # Call the shine remove command on the remote node with -L flag
        # to pass through the Local path of code.
        command = "%s remove -f %s -L" % (self.progpath, self.fs.fs_name)

        # Run cluster command
        self.task.shell(command, nodes=self.nodes, handler=self)
        self.task.resume()

    def ev_read(self, worker):
        """
        Function called each time a new message is read from a 
        a remote node.
        """
        # Get the message sent by the remote nodes
        pass

    def ev_close(self, worker):
        for rc, nodelist in worker.iter_retcodes():
            # If the return code of the remote command is not 0
            # something goes wrong.
            if rc != 0:
                # Raise an exception for the error
                print "Remove of file system %s failed on %s" \
                        % (self.fs.fs_name, NodeSet.fromlist(nodelist))
            else:
                # Print a success message
                print "File system %s successfully removed on %s" \
                        % (self.fs.fs_name, NodeSet.fromlist(nodelist))

        # Retrieve the list of file system client
        client_status_dict = self.fs.config.get_status_clients()

        # If there is some client for this file system we have to
        # unregister each of them from the backend
        if not client_status_dict == None:
            node_list=[]
            
            for node in client_status_dict.keys():
                node_list.append(node)
                
            # Unregister all the file system client
            self.fs.config.unregister_clients(node_list)

        # Unregister file system configuration from the backend
        self.fs.config.unregister_fs()
        
        

