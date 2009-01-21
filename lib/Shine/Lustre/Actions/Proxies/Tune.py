# Tune.py -- Lustre proxy action class : start
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
import os

class Tune(ProxyAction):
    """
    File system Tune proxy action class.
    """

    def __init__(self, task, fs, nodes, tuning_model):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.nodes = nodes
        self.tuning_model = tuning_model
        
        self.node_failure_messages={}

    def launch(self):
        """
        Proxy file system Tune command to target.
        """

        # Walk through the list of nodes registered in the node set and
        # retrieve each tuning parameters that must be applied to it.
        command = "%s tune -f %s -R " % (self.progpath, self.fs.fs_name)

        # Run cluster command
        self.task.shell(command, nodes=self.nodes, handler=self)
            
        self.task.resume()

    def ev_read(self, worker):
        """
        Function called each time a new message is read from a 
        a remote node.
        """
        # Get the message sent by the remote nodes
        (node_name, buffer) = worker.last_read()

        dic = self._read_shine_msg(buffer)
                
        # Process valid messages
        if not dic == None:
            
            # Parse the RESULT message to determine is the tuning operation
            # has succeeded or not.
            if dic['msg'] == 'RESULT':
            
                # Is it an error report ?
                if not dic['rc'] == 0:
                    # Some tuning operations have failed
                    
                    if not self.node_failure_messages.has_key(node_name):
                        # If not error message have alredy been registered for
                        # this node we need to initialize the dictionnary with
                        # a list for this node
                        self.node_failure_messages[node_name] = list()
                    
                    if dic['parameter_name'] not in \
                            self.node_failure_messages[node_name]:
                        self.node_failure_messages[node_name].append( \
                                dic['parameter_name'])

    def ev_close(self, worker):
        # Process messages send by the remote nodes
        if not len(self.node_failure_messages) == 0:
            
            failed_nodes = NodeSet()
            first = True
            
            # Walk through the node failure message dictionary to display
            # error messages
            for (node_name, parameters) in self.node_failure_messages.items():
                print "Tuning failed on node %s for parameter(s) %s" % \
                        (node_name, parameters)
                
                failed_nodes.add(node_name)
                
            # Raise an exception for the error
            raise ActionFailedError(1, "Tuning of file system %s failed on %s" \
                    %(self.fs.fs_name, failed_nodes))
        else:
            # Print a success message
            print "File system %s successfully Tuned on %s" \
                    %(self.fs.fs_name, self.nodes)
