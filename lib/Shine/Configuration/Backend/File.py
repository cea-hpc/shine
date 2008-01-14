# File.py -- File backend module
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

from Backend import Backend
from FileSupport.Storage import Storage
from Shine.Configuration.Globals import Globals
from Shine.Configuration.TargetDevice import TargetDevice

import os
import shelve

class File(Backend):

    def __init__(self):
        Backend.__init__(self)
        self.storage_file = None
        self.status_clients = {}

    def get_name(self):
        return "file"

    def get_desc(self):
        return "File Backend System."

    def start(self):
        pass

    def stop(self):
        #print "BACKEND STOP"
        for d in self.status_clients.itervalues():
            d.close()
        self.status_clients = {}

    def _start_storage(self):
        self.storage_file = Storage(Globals().get_storage_file())

    def _start_status_client(self, fs_name):

        status_dir = Globals().get_cache_dir()
        if not os.path.exists(status_dir):
            os.mkdir(status_dir)

        status_file = os.path.join(status_dir, fs_name)

        print "Starting status client for FS %s" % fs_name
        self.status_clients[fs_name] =  shelve.open(status_file)

    def get_target_devices(self, target):
        """Get target storage devices"""
        if not self.storage_file:
            self._start_storage()
        return self.storage_file.get_target_devices(target)

    def set_status_client(self, fs_name, node, status, options):
        """Set status of file system client."""
        if not self.status_clients.has_key(fs_name):
            self._start_status_client(fs_name)

        sta = { Backend.MOUNT_COMPLETE  : "m_complete",
                Backend.MOUNT_FAILED    : "m_failed",
                Backend.MOUNT_WARNING   : "m_warning",
                Backend.UMOUNT_COMPLETE : "u_complete",
                Backend.UMOUNT_FAILED   : "u_failed",
                Backend.UMOUNT_WARNING  : "u_warning"
              }
        
        if not sta.has_key(status):
            raise BackendInvalidParameterError()

        d = self.status_clients[fs_name]
        d[node] = { 'options' : options, 'status' : sta[status] }
        d.close()
        
