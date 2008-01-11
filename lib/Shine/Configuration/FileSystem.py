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

from Backend.BackendRegistry import BackendRegistry

from Backend.Backend import Backend

import copy
import os


class FileSystem(Model):
    """
    Lustre File System Configuration class.
    """
    def __init__(self, fs_name=None, lmf=None):
        """ Initialize File System config
        """
        # XXX Start the selected config backend system. XXX
        self.backend = BackendRegistry().get_selected()
        self.backend.start()

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

        self.fs_name = self.get_one('fs_name')


    def _setup_target_devices(self):
        """ Generate the eXtended Model File XMF
        """
        for target in [ 'mgt', 'mdt', 'ost' ]:

            # Returns a list of TargetDevices
            candidates = copy.copy(self.backend.get_target_devices(target))

            # Save the model target selection
            target_models = copy.copy(self.get(target))

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

        # Create new XMF path
        #self.xmf_path = "%s/%s.xmf" % (Globals().get_conf_dir(), self.get_one('fs_name'))
        # Save XMF
        self.save(self.xmf_path)
            
        
    def __str__(self):
        return ">> BACKEND:\n%s\n>> MODEL:\n%s" % (self.backend, Model.__str__(self))

    def close(self):
        if self.backend:
            self.backend.stop()
            self.backend = None
    
    def set_status_client_mount_complete(self, node, options):
        self.backend.set_status_client(self.fs_name, node,
            Backend.MOUNT_COMPLETE, options)

    def set_status_client_mount_failed(self, node, options):
        self.backend.set_status_client(self.fs_name, node,
            Backend.MOUNT_FAILED, options)

    def set_status_client_mount_warning(self, node, options):
        self.backend.set_status_client(self.fs_name, node,
            Backend.MOUNT_WARNING, options)

    def set_status_client_umount_complete(self, node, options):
        self.backend.set_status_client(self.fs_name, node,
            Backend.UMOUNT_COMPLETE, options)

    def set_status_client_umount_failed(self, node, options):
        self.backend.set_status_client(self.fs_name, node,
            Backend.UMOUNT_FAILED, options)

    def set_status_client_umount_warning(self, node, options):
        self.backend.set_status_client(self.fs_name, node,
            Backend.UMOUNT_WARNING, options)

