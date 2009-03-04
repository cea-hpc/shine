# Disk.py -- Pythonized Lustre Disk
# Copyright (C) 2009 CEA
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


"""
Lustre Disk abstraction module.

"""


import os
import stat
import struct
import tempfile

from ClusterShell.Task import task_self

### From lustre/include/lustre_disk.h:

# on-disk files
MDT_LOGS_DIR = "LOGS"
MOUNT_CONFIGS_DIR = "CONFIGS"
MOUNT_DATA_FILE = "%s/mountdata" % MOUNT_CONFIGS_DIR
LAST_RCVD = "last_rcvd"
LOV_OBJID = "lov_objid"
HEALTH_CHECK = "health_check"

# persistent mount data
LDD_F_SV_TYPE_MDT = 0x0001  # MDT
LDD_F_SV_TYPE_OST = 0x0002  # OST
LDD_F_SV_TYPE_MGS = 0x0004  # MGS
LDD_F_NEED_INDEX = 0x0010   # need an index assignment
LDD_F_VIRGIN = 0x0020       # never registered
LDD_F_UPDATE = 0x0040       # update all related config logs
LDD_F_REWRITE_LDD = 0x0080  # rewrite the LDD
LDD_F_WRITECONF = 0x0100    # regenerate all logs for this fs
LDD_F_UPGRADE14 = 0x0200    # COMPAT_14
LDD_F_PARAM = 0x0400        # process as lctl conf_param

# enum ldd_mount_type
LDD_MT_EXT3 = 0
LDD_MT_LDISKFS = 1
LDD_MT_SMFS = 2
LDD_MT_REISERFS = 3
LDD_MT_LDISKFS2 = 4
LDD_MT_LAST = 5

LDD_INCOMPAT_SUPP = 0
LDD_ROCOMPAT_SUPP = 0

LDD_MAGIC = 0x1dd00001

# From lustre-1.6.7/lustre/include/lustre_disk.h:
# 
# /* On-disk configuration file. In host-endian order. */
# struct lustre_disk_data {
#         __u32      ldd_magic;
#         __u32      ldd_feature_compat;  /* compatible feature flags */
#         __u32      ldd_feature_rocompat;/* read-only compatible feature flags */
#         __u32      ldd_feature_incompat;/* incompatible feature flags */
# 
#         __u32      ldd_config_ver;      /* config rewrite count - not used */
#         __u32      ldd_flags;           /* LDD_SV_TYPE */
#         __u32      ldd_svindex;         /* server index (0001), must match 
#                                            svname */
#         __u32      ldd_mount_type;      /* target fs type LDD_MT_* */
#         char       ldd_fsname[64];      /* filesystem this server is part of */
#         char       ldd_svname[64];      /* this server's name (lustre-mdt0001)*/
#         __u8       ldd_uuid[40];        /* server UUID (COMPAT_146) */
# 
# /*200*/ char       ldd_userdata[1024 - 200]; /* arbitrary user string */
# /*1024*/__u8       ldd_padding[4096 - 1024];
# /*4096*/char       ldd_mount_opts[4096]; /* target fs mount opts */
# /*8192*/char       ldd_params[4096];     /* key=value pairs */
# };


class DiskException(Exception):
    def __init__(self, disk):
        self.disk = disk

class DiskError(DiskException):
    """
    Generic disk related error.
    """

class DiskDeviceError(DiskError):
    """
    Associated device error.
    """
    def __init__(self, disk, message):
        DiskError.__init__(self, disk)
        self.message = message

    def __str__(self):
        return self.message


class Disk:
    """
    Represents a low-level Lustre Disk as defined in lustre/include/
    lustre_disk.h. Base class for Lustre Target (see Target.py).
    """

    def __init__(self, dev, jdev=None):
        self.dev = dev
        self.jdev = jdev

        # filled by _device_check
        self.dev_isblk = False
        self.dev_size = 0

        # filled by _read_mountdata (use provided accessors)
        self._ldd_flags = 0

    def update(self, other):
        self.dev_isblk = other.dev_isblk
        self.dev_size = other.dev_size
        self._ldd_flags = other._ldd_flags

    def _disk_check(self):
        self._device_check()
        self._read_mountdata()

    def _device_check(self):
        """
        Device sanity checking based on the stat() syscall.
        """
        try:
            info = os.stat(self.dev)
        except OSError, e:
            raise DiskDeviceError(self, str(e))

        mode = info[stat.ST_MODE]

        if stat.S_ISBLK(mode):
            # block device
            self.dev_isblk = True
            # get dev size
            f = open("/proc/partitions", 'r')
            try:
                dev = os.path.basename(self.dev)
                for line in f:
                    d_info = line.rstrip('\n').split(' ')
                    if len(d_info) > 1 and d_info[-1] == dev:
                        self.dev_size = int(d_info[-2]) * 1024
                        break
            finally:
                f.close()

        elif stat.S_ISREG(mode):
            # regular file
            self.dev_isblk = False
            self.dev_size = int(info[stat.ST_SIZE])
        else:
            # unsupported
            raise DiskDeviceError(self, "unsupported device type")

    def _read_mountdata(self):
        """
        Read CONFIGS/mountdata.
        """

        task = task_self()
        tmp_dir = tempfile.mkdtemp()

        debugfs = task.shell("debugfs -c -R 'dump /%s %s/mountdata' '%s'" % \
                (MOUNT_DATA_FILE, tmp_dir, self.dev), timeout=0)

        task.resume()

        print debugfs.retcode()
        # XXX check for timeout

        tmp_mountdata = os.path.join(tmp_dir, "mountdata")

        f = open(tmp_mountdata, "r")
        try:
            bytes = f.read(160)
            required_bytes = struct.calcsize('IIIIIIII64s64s')
            if len(bytes) < required_bytes:
                # err
                pass

            else:
                (ldd_magic, ldd_feat_compat, ldd_feat_rocompat, fdd_feat_incompat,
                        ldd_config_ver, ldd_flags, ldd_svindex, ldd_mount_type,
                        ldd_fsname, ldd_svname) = struct.unpack('IIIIIIII64s64s', bytes)

                assert ldd_magic == LDD_MAGIC

                ldd_fsname = ldd_fsname.rstrip('\0')

                ldd_svname = ldd_svname.rstrip('\0')

                # XXX

            self._ldd_flags = ldd_flags

        finally:
            f.close()
            os.unlink(tmp_mountdata)
            os.rmdir(tmp_dir)

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

