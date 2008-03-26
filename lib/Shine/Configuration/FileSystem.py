# FileSystem.py -- Lustre file system configuration
# Copyright (C) 2007 CEA
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

from Shine.Utilities.Cluster.NodeSet import NodeSet

from NidMap import NidMap

import copy
import os


class FileSystem(Model):
    """
    Lustre File System Configuration class.
    """
    def __init__(self, fs_name=None, lmf=None):
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

    def _start_backend(self):
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
                if len(result) == 0:
                    raise ConfigDeviceNotFoundError(target_model)
                for matching in result:
                    candidates.remove(matching)
                    self.add(target, matching.getline())

        # Save XMF
        self.save(self.xmf_path, "Shine Lustre file system config file for %s" % self.get_one('fs_name'))
            
    def _setup_nid_map(self, maps):

        self.nid_map = NidMap().fromlist(maps)
        #DEBUGprint self.nid_map
        #print self.get_nid('fortoy30')

    def get_nid(self, node):
            return self.nid_map[node]

    def __str__(self):
        return ">> BACKEND:\n%s\n>> MODEL:\n%s" % (self.backend, Model.__str__(self))

    def close(self):
        if self.backend:
            self.backend.stop()
            self.backend = None
    
    def set_status_client_mount_complete(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            Backend.MOUNT_COMPLETE, options)

    def set_status_client_mount_failed(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            Backend.MOUNT_FAILED, options)

    def set_status_client_mount_warning(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            Backend.MOUNT_WARNING, options)

    def set_status_client_umount_complete(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            Backend.UMOUNT_COMPLETE, options)

    def set_status_client_umount_failed(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            Backend.UMOUNT_FAILED, options)

    def set_status_client_umount_warning(self, node, options):
        self._start_backend()
        self.backend.set_status_client(self.fs_name, node,
            Backend.UMOUNT_WARNING, options)

    def get_status_clients(self):
        self._start_backend()
        return self.backend.get_status_clients(self.fs_name)

