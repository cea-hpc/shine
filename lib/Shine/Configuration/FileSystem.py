# FileSystem.py -- Lustre file system configuration
# Copyright (C) 2007, 2008 CEA
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


from Globals import Globals
from Model import Model
from Exceptions import *
from TuningModel import TuningModel

from ClusterShell.NodeSet import NodeSet

from NidMap import NidMap

import copy
import os
import sys


class FileSystem(Model):
    """
    Lustre File System Configuration class.
    """
    def __init__(self, fs_name=None, lmf=None, tuning_file=None):
        """ Initialize File System config
        """
        self.backend = None

        globals = Globals()

        fs_conf_dir = os.path.expandvars(globals.get_conf_dir())
        fs_conf_dir = os.path.normpath(fs_conf_dir)

        # Load the file system from model or extended model
        if not fs_name and lmf:
            print "Loading File System from LMF %s" % lmf
            Model.__init__(self, lmf)

            self.xmf_path = "%s/%s.xmf" % (fs_conf_dir, self.get_one('fs_name'))

            self._setup_target_devices()

            # Reload
            self.set_filename(self.xmf_path)

        elif fs_name:
            self.xmf_path = "%s/%s.xmf" % (fs_conf_dir, fs_name)
            Model.__init__(self, self.xmf_path)

        self._setup_nid_map(self.get('nid_map'))

        self.fs_name = self.get_one('fs_name')
        
        # Initialize the tuning model to None if no special tuning configuration
        # is provided
        self.tuning_model = None
        
        if tuning_file:
            # It a tuning configuration file is provided load it
            self.tuning_model = TuningModel(tuning_file)
        else:
            self.tuning_model = TuningModel()

        #self._start_backend()

    def _start_backend(self):
        """
        Load and start backend subsystem once
        """
        if not self.backend:

            from Backend.BackendRegistry import BackendRegistry
            from Backend.Backend import Backend

            # Start the selected config backend system.
            self.backend = BackendRegistry().get_selected()
            self.backend.start()

    def _setup_target_devices(self):
        """ Generate the eXtended Model File XMF
        """
        self._start_backend()

        for target in [ 'mgt', 'mdt', 'ost' ]:

            # Returns a list of TargetDevices
            candidates = copy.copy(self.backend.get_target_devices(target))

            try:
                # Save the model target selection
                target_models = copy.copy(self.get(target))
            except KeyError, e:
                raise ConfigException("No %s target found" %(target))

            # To be replaced...
            self.delete(target)
             
            # Iterates on ModelDevices
            for target_model in target_models:
                result = target_model.match_device(candidates)
                if len(result) == 0 and not target == 'mgt' :
                    raise ConfigDeviceNotFoundError(target_model)
                for matching in result:
                    candidates.remove(matching)
                    self.add(target, matching.getline())

        # Save XMF
        self.save(self.xmf_path, "Shine Lustre file system config file for %s" % self.get_one('fs_name'))
            
    def _setup_nid_map(self, maps):
        """
        Set self.nid_map using the NidMap helper class
        """
        self.nid_map = NidMap().fromlist(maps)

    def get_nid(self, node):
        try:
            return self.nid_map[node]
        except KeyError:
            print "Cannot get NID for %s, aborting. Please verify `nid_map' configuration." % node
            # FIXME : raise fatal exception
            sys.exit(1)

    def __str__(self):
        return ">> BACKEND:\n%s\n>> MODEL:\n%s" % (self.backend, Model.__str__(self))

    def close(self):
        if self.backend:
            self.backend.stop()
            self.backend = None
    
    def register_client(self, node):
        """
        This function aims to register a new client that will be able to mount the
        file system.
        Parameters:
        @type node: string
        @param node : is the new client node name
        """
        self._start_backend()
        self.backend.register_client(self.fs_name, node)
        
    def unregister_client(self, node):
        """
        This function aims to unregister a client of this  file system
        Parameters:
        @type node: string
        @param node : is name of the client node to unregister
        """
        self._start_backend()
        self.backend.unregister_client(self.fs_name, node)
    
    def set_status_client_mount_complete(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            self.backend.MOUNT_COMPLETE, options)

    def set_status_client_mount_failed(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            self.backend.MOUNT_FAILED, options)

    def set_status_client_mount_warning(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            self.backend.MOUNT_WARNING, options)

    def set_status_client_umount_complete(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            self.backend.UMOUNT_COMPLETE, options)

    def set_status_client_umount_failed(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            self.backend.UMOUNT_FAILED, options)

    def set_status_client_umount_warning(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            self.backend.UMOUNT_WARNING, options)

    def get_status_clients(self):
        self._start_backend()
        return self.backend.get_status_clients(self.fs_name)

    def set_status_target_unknown(self, target, options):
        """
        This function is used to set the specified target status
        to UNKNOWN
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, node, 
            self.backend.TARGET_UNKNOWN, options)

    def set_status_target_ko(self, target, options):
        """
        This function is used to set the specified target status
        to KO
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            backend.TARGET_KO, options)

    def set_status_target_available(self, target, options):
        """
        This function is used to set the specified target status
        to AVAILABLE
        """
        self._start_backend()
        # Set the fs_name to Free since these targets are availble
        # which means not used by any file system.
        self.backend.set_status_target(None, target,
            self.backend.TARGET_AVAILABLE, options)

    def set_status_target_formating(self, target, options):
        """
        This function is used to set the specified target status
        to FORMATING
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_FORMATING, options)

    def set_status_target_format_failed(self, target, options):
        """
        This function is used to set the specified target status
        to FORMAT_FAILED
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_FORMAT_FAILED, options)

    def set_status_target_formated(self, target, options):
        """
        This function is used to set the specified target status
        to FORMATED
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_FORMATED, options)

    def set_status_target_offline(self, target, options):
        """
        This function is used to set the specified target status
        to OFFLINE
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_OFFLINE, options)

    def set_status_target_starting(self, target, options):
        """
        This function is used to set the specified target status
        to STARTING
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_STARTING, options)

    def set_status_target_online(self, target, options):
        """
        This function is used to set the specified target status
        to ONLINE
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_ONLINE, options)

    def set_status_target_critical(self, target, options):
        """
        This function is used to set the specified target status
        to CRITICAL
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_CRITICAL, options)

    def set_status_target_stopping(self, target, options):
        """
        This function is used to set the specified target status
        to STOPPING
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_STOPPING, options)

    def set_status_target_unreachable(self, target, options):
        """
        This function is used to set the specified target status
        to UNREACHABLE
        """
        self._start_backend()
        self.backend.set_status_target(self.fs_name, target, 
            self.backend.TARGET_UNREACHABLE, options)

    def get_status_targets(self):
        """
        This function returns the status of each targets
        involved in the current file system.
        """
        self._start_backend()
        return self.backend.get_status_targets(self.fs_name)

    def register(self):
        """
        This function aims to register the file system configuration
        to the backend.
        """
        self._start_backend()
        return self.backend.register_fs(self)

    def unregister(self):
        """
        This function aims to remove a file system configuration from
        the backend.        
        """
        self._start_backend()
        result = self.backend.unregister_fs(self)

        # remove the XMF file
        os.unlink(self.xmf_path)

        return result
