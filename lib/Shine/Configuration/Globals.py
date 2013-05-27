# Globals.py -- Configuration of global parameters
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

GLOBAL_CONF_FILE="/etc/shine/shine.conf"

from ModelFile import ModelFile

class Globals(object):
    """
    Global paramaters configuration class.
    Design Pattern: Singleton
    """
    __instance = None

    def __new__(cls):
        if not Globals.__instance:
            Globals.__instance = Globals.__Globals()
        return Globals.__instance

    def __getattr__(self, attr):
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, val):
        return setattr(self.__instance, attr, val)

    class __Globals(ModelFile):
        
        syntax = {
            'backend'                   : ['clusterdb', 'file'],
            'storage_file'              : 'path',
            'cache_dir'                 : 'path',
            'conf_dir'                  : 'path',
            'tuning_file'               : 'path',
            'ssh_connect_timeout'       : 'digit',
            'install_timeout'           : 'digit',
            'start_timeout'             : 'digit',
            'mount_timeout'             : 'digit',
            'umount_timeout'            : 'digit',
            'stop_timeout'              : 'digit',
            'status_timeout'            : 'digit',
            'disable_nagios'            : ['yes', 'no'],
            'disable_chkconfig_for_ldap': ['yes', 'no'],
            'use_stormap_for_chk_dev'   : ['yes', 'no'],
            'set_ioscheds_timeout'      : 'digit',
            'allow_loop_devices'        : ['yes', 'no'],
            'default_fanout'            : 'digit',
            'check_only_mounted_nodes_on_mnt_status' : ['yes', 'no'],
            'set_tuning_timeout'        : 'digit',
            'disable_modules_unloading' : ['yes', 'no'],
            'disable_mgmt_node_test'    : ['yes', 'no'],
            'plugin'                    : 'string'
        }

        def __init__(self, path=GLOBAL_CONF_FILE):
            ModelFile.__init__(self, path, "=")

        def get_backend(self):
            return self.get_one('backend')

        def get_storage_file(self):
            return self.get_one('storage_file')

        def get_cache_dir(self):
            return self.get_one('cache_dir')

        def get_conf_dir(self):
            return self.get_one('conf_dir')

        def get_tuning_file(self):
            return self.get_one('tuning_file')

        # ...
