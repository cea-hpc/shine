# Backend.py -- File system config backend point of view
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


NIEXC="Derived classes must implement."

class Backend:
    """
    An interface representing config backend storage resources for a file system.
    """

    MOUNT_COMPLETE = 1
    MOUNT_FAILED = 2
    MOUNT_WARNING = 3
    UMOUNT_COMPLETE = 4
    UMOUNT_FAILED = 5
    UMOUNT_WARNING = 6

    # Integers which represents the different target status
    TARGET_UNKNOWN=1
    TARGET_KO=2
    TARGET_AVAILABLE=3
    TARGET_FORMATING=4
    TARGET_FORMAT_FAILED=5
    TARGET_FORMATED=6
    TARGET_OFFLINE=7
    TARGET_STARTING=8
    TARGET_ONLINE=9
    TARGET_CRITICAL=10
    TARGET_STOPPING=11
    TARGET_UNREACHABLE=12
    TARGET_CHECKING=13

    # Integers which represents the different fs status
    FS_INSTALLED = 1
    FS_FORMATING = 2
    FS_FORMATED = 3
    FS_STARTING = 4
    FS_ONLINE = 5
    FS_MOUNTED = 6
    FS_STOPPING = 7
    FS_OFFLINE  = 8
    FS_CHECKING = 9
    FS_UNKNOWN = 10
    FS_WARNING = 11
    FS_CRITICAL = 12
    FS_ONLINE_FAILED = 13
    FS_OFFLINE_FAILED = 14
    FS_FORMAT_FAILED = 15

    def __init__(self):
        "Initializer."
        pass

    # Public accessors.

    def get_name(self):
        raise NotImplementedError(NIEXC)

    def get_desc(self):
        raise NotImplementedError(NIEXC)

    # Public methods.

    def start(self):
        """
        The config backend storage system has been selected.
        """
        raise NotImplementedError(NIEXC)

    def stop(self):
        """
        Stop operations
        """
        raise NotImplementedError(NIEXC)

    def get_target_devices(self, target):
        """
        Get the targets configuration, as a TargetDevice list (for mgt, mdt, ost).
        """
        raise NotImplementedError(NIEXC)

    def set_status_client(self, fs_name, node, status, options):
        """
        Set status of file system client.
        """
        raise NotImplementedError(NIEXC)

    def get_status_clients(self, fs_name):
        """
        Get all client's status of the form { node1 : { 'status' : status,
        'date' : datetime, 'options' : None }, node2 : ... }
        """
        raise NotImplementedError(NIEXC)
    
    def set_status_target(self, fs_name, targets, status, options):
        """
        Set status of file system target.
        """
        raise NotImplementedError(NIEXC)

    def get_status_target(self, fs_name):
        """
        Get all target status of the form { target1 : { 'status' : status, 
        'date' : datetime, 'options' : None }, target2 : ... }
        """
        raise NotImplementedError(NIEXC)

    def register_fs(self, fs):
        """
        This function is used to register a a filesystem configuration to the backend
        """
        raise NotImplementedError(NIEXC)

    def unregister_fs(self, fs):
        """
        This function is used to remove a filesystem configuration to the backend
        """
        raise NotImplementedError(NIEXC)

    def set_status_fs(self, fs_name, status, options):
        """
        Set status of file system.
        """
        raise NotImplementedError(NIEXC)

    def get_status_fs(self, fs_name):
        """
        Get all target status of the form { fs : { 'status' : status,
        'date' : datetime, 'options' : None } }
        """
        raise NotImplementedError(NIEXC)

    def register_client(self, fs, node):
        """
        This function is used to register a filesystem client to the backend
        """
        raise NotImplementedError(NIEXC)

    def unregister_client(self, fs, node):
        """
        This function is used to remove a filesystem client from the backend
        """
        raise NotImplementedError(NIEXC)
