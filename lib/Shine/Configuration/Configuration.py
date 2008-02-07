# Configuration.py -- Configuration container
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
from FileSystem import FileSystem

class Target:
    def __init__(self, type, cf_target):
        self.type = type
        self.dic = cf_target.get_dict()

    def get_type(self):
        return self.type

    def get_name(self):
        return self.dic.get('name')
        
    def get_nodename(self):
        return self.dic.get('node_name')

    def get_dev(self):
        return self.dic.get('dev')

    def get_dev_size(self):
        return self.dic.get('size')

    def get_jdev(self):
        return self.dic.get('jdev')

    def get_jdev_size(self):
        return self.dic.get('jsize')
    

class Configuration:
    def __init__(self, fs_name=None, lmf=None):
        """FS configuration initializer."""

        # Initialize FS configuration
        if fs_name or lmf:
            self._fs = FileSystem(fs_name, lmf)
        else:
            self._fs = None

        #DEBUG#print self._fs

    def __str__(self):
        s = "> GLOBALS:\n%s" % Globals.GLOBALS
        if self._fs:
            s = s + "\n> FILESYSTEM:\n%s" % self._fs
        else:
            s = s + "\n> NO FILESYSTEM"
        return s

    def close(self):
        self._fs.close()

    ###

    def get_target_mgt(self):
        tgt_cf_list = self._fs.get('mgt')
        return Target('MGT', tgt_cf_list[0])

    def get_target_mdt(self):
        tgt_cf_list = self._fs.get('mdt')
        return Target('MDT', tgt_cf_list[0])

    def iter_targets_ost(self):
        tgt_cf_list = self._fs.get('ost')
        for t in tgt_cf_list:
            yield Target('OST', t)

    # General FS getters
    #
    def get_fs_name(self):
        return self._fs.get_one('fs_name')

    def get_cfg_filename(self):
        """
        Return FS xmf file path.
        """
        return self._fs.get_filename()

    def get_description(self):
        return self._fs.get_one('description')

    def get_quota(self):
        return self._fs.get_one('quota')

    def get_mount_path(self):
        return self._fs.get_one('mount_path')
        

    # Stripe info getters
    #
    def get_stripecount(self):
        if self._fs.has_key('stripe_count'):
            return int(self._fs.get_one('stripe_count'))
        return None

    def get_stripesize(self):
        if self._fs.has_key('stripe_size'):
            return int(self._fs.get_one('stripe_size'))
        return None

    def get_nettype(self):
        if self._fs.has_key('nettype'):
            return self._fs.get_one('nettype')
        # default is tcp
        return "tcp"

    # Target status setters
    #
    #def set_target_status(self, ...):
    #    pass

    def set_status_clients_mount_complete(self, nodes, options):
        for node in nodes:
            self._fs.set_status_client_mount_complete(node, options)

    def set_status_clients_mount_failed(self, nodes, options):
        for node in nodes:
            self._fs.set_status_client_mount_failed(node, options)

    def set_status_clients_mount_warning(self, nodes, options):
        for node in nodes:
            self._fs.set_status_client_mount_warning(node, options)

    def set_status_clients_umount_complete(self, nodes, options):
        for node in nodes:
            self._fs.set_status_client_umount_complete(node, options)

    def set_status_clients_umount_failed(self, nodes, options):
        for node in nodes:
            self._fs.set_status_client_umount_failed(node, options)

    def set_status_clients_umount_warning(self, nodes, options):
        for node in nodes:
            self._fs.set_status_client_umount_warning(node, options)

