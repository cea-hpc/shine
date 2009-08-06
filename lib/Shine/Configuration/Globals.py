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
import logging


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
            'backend'                   : ['ClusterDB', 'File', 'None'],
            'storage_file'              : 'path',
            'status_dir'                : 'path',
            'conf_dir'                  : 'path',
            'lmf_dir'                   : 'path',
            'tuning_file'               : 'path',
            'log_file'                  : 'path',
            'log_level'                 : [ 'debug', 'info', 'warn', 'error' ],
            'ssh_connect_timeout'       : 'digit',
            'default_timeout'           : 'digit',
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

        defaults = {
            'backend'                   : 'None',
            'storage_file'              : '/etc/shine/storage.conf',
            'status_dir'                : '/var/cache/shine/status',
            'conf_dir'                  : '/var/cache/shine/conf',
            'lmf_dir'                   : '/etc/shine/models',
            'tuning_file'               : '',
            'log_file'                  : 'warn',
            'log_level'                 : 'warn',
            'ssh_connect_timeout'       : 0,
            'default_timeout'           : 30,
            'start_timeout'             : 0,
            'mount_timeout'             : 0,
            'umount_timeout'            : 0,
            'stop_timeout'              : 0,
            'status_timeout'            : 0, 
            'disable_nagios'            : 'yes',
            'disable_chkconfig_for_ldap': 'yes',
            'use_stormap_for_chk_dev'   : 'yes',
            'set_ioscheds_timeout'      : 0,
            'allow_loop_devices'        : 'yes',
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

        def get_status_dir(self):
            return self.get_one('status_dir')

        def get_conf_dir(self):
            return self.get_one('conf_dir')

        def get_lmf_dir(self):
            return self.get_one('lmf_dir')

        def get_tuning_file(self):
            return self.get_one('tuning_file')

        def get_log_file(self):
            return self.get_one('log_file')

        def get_log_level(self):
            levels = { 'debug' : logging.DEBUG,
                       'info' : logging.INFO,
                       'warn' : logging.WARN,
                       'error' : logging.ERROR }

            return levels[self.get_one('log_level')]

        def get_default_timeout(self):
            return float(self.get_one('default_timeout'))

        def get_status_timeout(self):
            return float(self.get_one('status_timeout'))

        # ...
