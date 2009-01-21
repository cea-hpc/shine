# Install.py -- Install Lustre FS configuration
# Copyright (C) 2007 BULL S.A.S
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

# Import Section
from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.TuningModel import TuningModel
from Shine.Configuration.TuningModel import TuningParameterDeclarationException

from Shine.Commands.CommandRegistry import CommandRegistry
from Action import Action, ActionFailedError

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker

import os
import sys
import socket
import binascii
import pickle

class Tune(Action):
    """
    Action class: Remote file system configuration requirements on remote
    nodes.
    """

    def __init__(self, task, fs, tuning_filename):
        Action.__init__(self, task)
        self.fs = fs
        self.tuning_filename = tuning_filename
        self.worker_dict=dict()

    def launch(self):
        """
        Do it.
        """
        type_list = self.fs.config.get_localnode_type()
        
        # Is the tuning configuration file name specified ?
        if self.tuning_filename.strip() == "":
            # No.  Create an empty tuning model.
            tuning_model = TuningModel()
        else:
            # Yes.
            # Load the tuning configuration file
            tuning_model = TuningModel(self.tuning_filename)
        
            try:
                # Parse it
                tuning_model.parse()
                
                # Add the quota tuning parameters to the tuning model.
                self.fs.add_quota_tuning(tuning_model)
                
            except TuningParameterDeclarationException, tpde:
                # An error has occured during parsing of tuning configuration file
                print "%s" %(str(tpde))
                # FIXME: Maybe we have to do something better here !
                return
        
        # Retrieve the list of tuning parameters that must be applied to
        # the current node
        tuning_parameters = tuning_model.get_params_for_name( \
                socket.gethostname(), type_list)
        
        # Walk through the tuning parametere list and apply each one of them
        for tuning_parameter in tuning_parameters:
            # Build the command which must be executed on this node
            # to Tune de file system.
            command_list = tuning_parameter.build_tuning_command( \
                    self.fs.fs_name)
            
            # Walk through the list of commands created for this parameters
            # and create a shell for each one of them
            for command in command_list:
                
                self.worker_dict[id(self.task.shell(command, handler=self))] = \
                        tuning_parameter.get_parameter_name()

        self.task.resume()

    def ev_start(self, worker):
        # send a message for the start of the Tune process
        CommandRegistry.output(msg="TUNING")

        sys.stdout.flush()

    def ev_close(self, worker):
        # Send a message with the result of the tuning command
        CommandRegistry.output(msg="RESULT",
                               node = socket.gethostname(), 
                               rc = worker.retcode(),
                               parameter_name=self.worker_dict[id(worker)],
                               buf = worker.read(),
                               command = worker.command)
        
        sys.stdout.flush()
