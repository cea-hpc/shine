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
        """The config backend storage system has been selected."""
        raise NotImplementedError(NIEXC)

    def stop(self):
        """Stop operations"""
        raise NotImplementedError(NIEXC)
        

    def get_target_devices(self, target):
        """Get the targets configuration, as a TargetDevice list (for mgt, mdt, ost)."""
        raise NotImplementedError(NIEXC)

    def set_status_client(self, fs_name, nodes, status, options):
        """Set status of file system client."""
        raise NotImplementedError(NIEXC)


