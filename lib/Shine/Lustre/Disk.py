# Disk.py -- Pythonized Lustre Disk
# Copyright (C) 2009-2013 CEA
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


"""
Lustre Disk abstraction module.
"""

import copy
import errno
import os
import stat
import subprocess

from Shine.Configuration.Globals import Globals

### From lustre/include/lustre_disk.h:

# persistent mount data
LDD_F_NEED_INDEX = 0x0010   # need an index assignment
LDD_F_VIRGIN = 0x0020       # never registered
LDD_F_UPDATE = 0x0040       # update all related config logs
LDD_F_REWRITE_LDD = 0x0080  # rewrite the LDD
LDD_F_WRITECONF = 0x0100    # regenerate all logs for this fs
LDD_F_UPGRADE14 = 0x0200    # COMPAT_14
LDD_F_PARAM = 0x0400        # process as lctl conf_param


class DiskDeviceError(Exception):
    """
    Associated device error.
    """
    def __init__(self, disk, message=None):
        Exception.__init__(self, message)
        self._disk = disk

class DiskNoDeviceException(Exception):
    """
    No device found.
    """
    def __init__(self, disk):
        Exception.__init__(self)
        self._disk = disk


class Disk:
    """
    Represents a low-level Lustre Disk as defined in lustre/include/
    lustre_disk.h. Base class for Lustre Target (see Target.py).
    """

    def __init__(self, dev):
        self.dev = dev

        # filled by _device_check
        self.dev_isblk = False
        self.dev_size = 0

        # filled by _mountdata_check (use provided accessors if needed)
        self.ldd_svname = None
        self._ldd_flags = 0

    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        self.dev_isblk = other.dev_isblk
        self.dev_size = other.dev_size
        self.ldd_svname = copy.copy(other.ldd_svname)
        self._ldd_flags = other._ldd_flags

    def _device_check(self):
        """
        Device sanity checking based on the stat() syscall.
        """
        try:
            info = os.stat(self.dev)
        except OSError, error:
            if error.errno == errno.ENOENT:
                raise DiskNoDeviceException(self)
            else:
                raise DiskDeviceError(self, str(error))

        mode = info[stat.ST_MODE]

        if stat.S_ISBLK(mode):
            # block device
            self.dev_isblk = True
            # get dev size
            partitions = open("/proc/partitions", 'r')
            try:
                dev = os.path.basename(os.path.realpath(self.dev))
                for line in partitions:
                    d_info = line.rstrip('\n').split(' ')
                    if len(d_info) > 1 and d_info[-1] == dev:
                        self.dev_size = int(d_info[-2]) * 1024
                        break
            finally:
                partitions.close()

        elif stat.S_ISREG(mode):
            # regular file
            self.dev_isblk = False
            self.dev_size = int(info[stat.ST_SIZE])
        else:
            # unsupported
            raise DiskDeviceError(self, "unsupported device type")

    def _mountdata_check(self, label_check=None):
        """Read device flags using 'tunefs.lustre'"""

        cmd = "tunefs.lustre --dryrun %s" % self.dev
        path = Globals().get('command_path')
        if path:
            cmd = "export PATH=%s:${PATH}; %s" % (path, cmd)

        process = subprocess.Popen([cmd], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)
        output = process.communicate()[0]
        if process.returncode > 0:
            raise DiskDeviceError(self, "Failed to run 'tunefs.lustre' to " +
                                  "read flags (rc=%d)" % process.returncode)

        for line in output.splitlines():
            line = line.strip()
            if line.startswith('Flags:'):
                self._ldd_flags = int(line.split(':')[1], 16)
            elif line.startswith('Target:'):
                self.ldd_svname = line.split(':', 1)[1].strip()
            elif line.startswith('Permanent disk data:'):
                break

        if label_check:
            # Lustre 2.3 changed the label patterns.
            # fsname and svname could be separated by '-', ':' and '='
            # For compatibility reasons, we ignore ':' and '='.
            if len(self.ldd_svname) > 8 and self.ldd_svname[-8] in (':', '='):
                self.ldd_svname = "%s-%s" % (self.ldd_svname[:-8],
                                             self.ldd_svname[-7:])

            if self.ldd_svname != label_check:
                raise DiskDeviceError(self,
                     "Found service %s != %s on %s" %
                     (self.ldd_svname, label_check, self.dev))

    def flags(self):
        """Return a list of text flags set on this disk."""
        lst = []
        if self.has_need_index_flag():
            lst.append("need_index")
        if self.has_first_time_flag():
            lst.append("first_time")
        if self.has_update_flag():
            lst.append("update")
        if self.has_rewrite_ldd_flag():
            lst.append("rewrite_ldd")
        if self.has_writeconf_flag():
            lst.append("writeconf")
        if self.has_upgrade14_flag():
            lst.append("upgrade14")
        if self.has_param_flag():
            lst.append("conf_param")
        return lst

    def has_need_index_flag(self):
        """LDD flag: need an index assignment"""
        return self._ldd_flags & LDD_F_NEED_INDEX

    def has_first_time_flag(self):
        """LDD flag: never registered"""
        return self._ldd_flags & LDD_F_VIRGIN

    def has_update_flag(self):
        """LDD flag: update all related config logs"""
        return self._ldd_flags & LDD_F_UPDATE

    def has_rewrite_ldd_flag(self):
        """LDD flag: rewrite the LDD"""
        return self._ldd_flags & LDD_F_REWRITE_LDD

    def has_writeconf_flag(self):
        """LDD flag: regenerate all logs for this fs"""
        return self._ldd_flags & LDD_F_WRITECONF

    def has_upgrade14_flag(self):
        """LDD flag: COMPAT 14"""
        return self._ldd_flags & LDD_F_UPGRADE14

    def has_param_flag(self):
        """LDD flag: process as lctl conf_param"""
        return self._ldd_flags & LDD_F_PARAM

