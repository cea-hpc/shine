# File.py -- File backend module
# Copyright (C) 2007-2010 CEA
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

import os
import shelve

from Shine.Configuration.Backend.Backend import Backend
from Shine.Configuration.Globals import Globals
from Shine.Configuration.ModelFile import ModelFile
from Shine.Configuration.TargetDevice import TargetDevice

BACKEND_MODNAME = "File"


class Storage(ModelFile):
    """Storage file for backend File."""

    def __init__(self, sep=":", linesep="\n"):
        ModelFile.__init__(self, sep, linesep)
        self.add_custom('mgt', FileDevice(), multiple=True)
        self.add_custom('mdt', FileDevice(), multiple=True)
        self.add_custom('ost', FileDevice(), multiple=True)

    def get_target_devices(self, tgt_type):
        return [TargetDevice(tgt_type, tgt)
                for tgt in self.elements(tgt_type).as_dict()]


class FileDevice(ModelFile):
    """ModelFile sub element representing a Target."""

    def __init__(self, sep='=', linesep=' '):
        ModelFile.__init__(self, sep, linesep)
        self.add_element('tag',     check='string')
        self.add_element('node',    check='string')
        self.add_element('ha_node', check='string')
        self.add_element('dev',     check='path')
        self.add_element('size',    check='digit')
        self.add_element('jdev',    check='path')
        self.add_element('jsize',   check='digit')


class File(Backend):

    def __init__(self):
        Backend.__init__(self)
        self.storage_file = None
        self.status_clients = {}

    def get_name(self):
        return "File"

    def get_desc(self):
        return "File Backend System."

    def start(self):
        pass

    def stop(self):
        for cli in self.status_clients.itervalues():
            cli.close()
        self.status_clients = {}

    def _start_storage(self):
        storage = Storage()
        storage.load(Globals().get_storage_file())
        self.storage_file = storage

    def _start_status_client(self, fs_name):

        status_dir = Globals().get_status_dir()
        if not os.path.exists(status_dir):
            os.mkdir(status_dir)

        status_file = os.path.join(status_dir, fs_name)

        self.status_clients[fs_name] = shelve.open(status_file)

    def get_target_devices(self, target, fs_name=None, update_mode=None):
        """
        Get target storage devices.
        """
        if not self.storage_file:
            self._start_storage()
        return self.storage_file.get_target_devices(target)

    def set_status_client(self, fs_name, node, status, options):
        """
        Set status of file system client.
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

        d[node] = { 'options' : options,
                    'status' : sta[status],
                    'date' : datetime.now() }

        #print "status: %s" % d
        d.close()
        """

    def get_status_clients(self, fs_name):
        """
        Get all client's status of the form { node1 : { 'status' : status,
        'date' : datetime, 'options' : None }, node2 : ... }
        """
        if not self.status_clients.has_key(fs_name):
            self._start_status_client(fs_name)
        return self.status_clients[fs_name]

    def set_status_target(self, fs_name, targets, status, options):
        """
        Set status of file system target.
        """
        pass

    def get_status_target(self, fs_name):
        """
        Get all target status of the form { target1 : { 'status' : status,
        'date' : datetime, 'options' : None }, target2 : ... }
        """
        pass

    def register_fs(self, fs):
        """
        This function is used to register a a filesystem configuration to the backend
        """
        pass

    def unregister_fs(self, fs):
        """
        This function is used to remove a filesystem configuration to the backend
        """
        pass

    def set_status_fs(self, fs_name, status, options):
        """
        Set status of file system.
        """
        pass

    def get_status_fs(self, fs_name):
        """
        Get all target status of the form { fs : { 'status' : status,
        'date' : datetime, 'options' : None } }
        """
        pass

    def register_client(self, fs, node):
        """
        This function is used to register a filesystem client to the backend
        """
        print "backend register_client %s/%s" % (fs, node)

    def unregister_client(self, fs, node):
        """
        This function is used to remove a filesystem client from the backend
        """
        print "backend un_register_client %s/%s" % (fs, node)

    def register_target(self, fs, target):
        """
        Set the specified `target', used by `fs', as 'in use' in the backend.

        This target could not be use anymore for other filesystems.
        """
        pass

    def unregister_target(self, fs, target):
        """
        Set the specified `target', used by `fs', as available in the backend.

        This target could be now reuse, for other targets of the same
        filesystem or any other one.
        """
        pass
