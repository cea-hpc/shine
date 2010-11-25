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

from FileSystem import FileSystem

from ClusterShell.NodeSet import NodeSet

from Exceptions import ConfigException


import socket

class Target:
    def __init__(self, type, cf_target):
        self.type = type
        self.dic = cf_target.as_dict()

    def get_type(self):
        return self.type

    def get_tag(self):
        return self.dic.get('tag')
        
    def get_nodename(self):
        return self.dic.get('node')

    def ha_nodes(self):
        """
        Return ha_nodes list (failover hosts). An empty list is
        returned when no ha_nodes are provided.
        """
        nodes = self.dic.get('ha_node')
        if not nodes:
            nodes = []
        elif type(nodes) is not list:
            nodes = [nodes]
        return nodes

    def get_dev(self):
        return self.dic.get('dev')

    def get_dev_size(self):
        return self.dic.get('size')

    def get_jdev(self):
        return self.dic.get('jdev')

    def get_jdev_size(self):
        return self.dic.get('jsize')

    def get_index(self):
        return int(self.dic.get('index', 0))

    def get_group(self):
        return self.dic.get('group')
    
    def get_mode(self):
        return self.dic.get('mode', 'managed')

    def get_network(self):
        return self.dic.get('network')

class Clients:
    def __init__(self, cf_client):
        self.dic = cf_client.as_dict()

    def get_nodes(self):
        return self.dic.get('node')

    def get_mount_path(self):
        return self.dic.get('mount_path')
        

class Routers:
    def __init__(self, cf_router):
        self.dic = cf_router.as_dict()

    def get_nodes(self):
        return self.dic.get('node')

class Configuration:
    def __init__(self):
        """FS configuration initializer."""
        self.debug = False
        self._fs = None

    @classmethod
    def load_from_cache(cls, fsname):
        conf = Configuration()
        try:
            conf._fs = FileSystem.load_from_fsname(fsname)
        except ValueError, error:
            raise ConfigException(str(error))
        return conf

    @classmethod
    def create_from_model(cls, lmf):
        conf = Configuration()
        try:
            conf._fs = FileSystem.create_from_model(lmf)
        except ValueError, error:
            raise ConfigException(str(error))
        return conf

    def close(self):
        self._fs.close()

    ###
    def get_nid(self, who):
        return self._fs.get_nid(who)

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

    def iter_targets(self):
        """
        Return a generator over all FS targets.
        """
        for target_type in [ 'mgt', 'mdt', 'ost' ]:
            if target_type not in self._fs:
                continue
            tgt_cf_list = self._fs.get(target_type)
            for t in tgt_cf_list:
                yield Target(target_type, t)
        
    def get_target_from_tag_and_type(self, target_tag, target_type):
        """
        This function aims to retrieve a target look for it's type
        and it's tag.
        """
        target = None
            
        if target_type == 'MGT' or target_type == 'MGS' :
            # The target is the MGT
            target =  self.get_target_mgt()
        elif target_type == 'MDT':
            # The target is the MDT
            target = self.get_target_mdt()
        elif target_type == 'OST':
            # The target is an OST. Walk through the list of 
            # OSTs to retrieve the right one.
            for current_ost in self.iter_targets_ost():
                if current_ost.get_tag() == target_tag:
                    # The ost tag match the searched one.
                    # save the target and break the loop
                    target = current_ost
                    break
        else:
            # The target type is currently not supported by the
            # configuration
            raise ConfigException("Unknown target type %s" %target_type) 
                        
        return target

    def get_client_nodes(self):
        nodes = NodeSet()
        if 'client' in self._fs:
            cli_cf_list = self._fs.get('client')
        else:
            return nodes
        for c in cli_cf_list:
            clients = Clients(c)
            nodes.update(clients.get_nodes())
        return nodes

    def get_client_mounts(self, select_nodes=None):
        """
        Get clients different mount paths. Returns a dict where keys are
        mount paths and values are nodes.
        Optional argument select_nodes makes the result with these nodes only.
        """
        # build a dict where keys are mount paths
        mounts = {}
        # no client defined?
        if not 'client' in self._fs:
            return mounts
        cli_cf_list = self._fs.get('client')

        if not 'mount_path' in self._fs:
            raise ConfigException("mount_path not specified")
        default_path = self._fs.get('mount_path')

        remain_nodes = None
        if select_nodes:
            remain_nodes = NodeSet(select_nodes)

        for c in cli_cf_list:
            clients = Clients(c)
            concern_nodes = NodeSet(clients.get_nodes())
            if remain_nodes:
                concern_nodes.intersection_update(remain_nodes)
                remain_nodes.difference_update(concern_nodes)
            if len(concern_nodes) > 0:
                path = clients.get_mount_path()
                if not path:
                    path = default_path
                if mounts.has_key(path):
                    nodes = mounts[path]
                    nodes.update(concern_nodes)
                else:
                    mounts[path] = NodeSet(concern_nodes)
        
        if remain_nodes:
            # fill unknown nodes with default mount point
            if mounts.has_key(default_path):
                mounts[default_path].update(remain_nodes)
            else:
                mounts[default_path] = remain_nodes

        return mounts

    def get_client_mount(self, client):
        """
        Get mount path for a client.
        """
        mounts = self.get_client_mounts()
        for path, nodes in mounts.iteritems():
            if nodes.intersection_update(client):
                return path

        #print "Warning: path not found for client %s ??" % client
        return self._fs.get('mount_path')

    def iter_clients(self):
        """
        Iterate over (node, mount_path)
        """
        mounts = self.get_client_mounts()
        for path, nodes in mounts.iteritems():
            for node in nodes:
                yield node, path

    def iter_routers(self):
        """
        Iterate over (node)
        """
        if 'router' in self._fs:
            for elem in self._fs.get('router'):
                rtr = Routers(elem)
                yield rtr.get_nodes()

    def get_localnode_type(self):
        """
        Function used to known the Lustre target type supported by the local node
        for the current file system
        """
        # List of type supported by the local node
        type_list = []

        # Get the locahost name
        localhost_name = socket.gethostname()

        # Is the node registered as a client 
        if localhost_name in self.get_client_nodes():
            type_list.append('client')

        # Is the node registered as mdt
        if localhost_name == self.get_target_mdt().get_nodename():
            type_list.append('mds')

        # Is the node registered as mgt
        if localhost_name == self.get_target_mgt().get_nodename():
            type_list.append('mgs')

        # Is the node registered as an oss
        for oss_node in self.iter_targets_ost():

            # is the node the current oss
            if localhost_name == oss_node.get_nodename():
                type_list.append('oss')
                break

        return type_list

    # General FS getters
    #
    def get_fs_name(self):
        return self._fs.get('fs_name')

    def get_cfg_filename(self):
        """
        Return FS xmf file path.
        """
        return self._fs.xmf_path

    def get_tuning_cfg_filename(self):
        """
        Return the tuning.conf file path
        """
        self._fs.tuning_model.get_filename()

    def get_description(self):
        return self._fs.get('description')

    def has_quota(self):
        """
        Return if quota has been enabled in the configuration file.
        """
        return self._fs.get('quota') == 'yes'

    def get_quota_type(self):
        return self._fs.get('quota_type')

    def get_quota_bunit(self):
        return self._fs.get('quota_bunit')

    def get_quota_iunit(self):
        return self._fs.get('quota_iunit')

    def get_quota_btune(self):
        return self._fs.get('quota_btune')

    def get_quota_itune(self):
        return self._fs.get('quota_itune')

    def get_mount_path(self):
        return self._fs.get('mount_path')

    def get_mount_options(self):
        return self._fs.get('mount_options')

    def get_target_mount_options(self, target):
        return self._fs.get('%s_mount_options' % str(target).lower())

    def get_target_mount_path(self, target):
        return self._fs.get('%s_mount_path' % str(target).lower())

    def get_target_format_params(self, target):
        return self._fs.get('%s_format_params' % str(target).lower())

    def get_target_mkfs_options(self, target):
        return self._fs.get('%s_mkfs_options' % str(target).lower())

    # Stripe info getters
    #
    def get_stripecount(self):
        return self._fs.get('stripe_count', None)

    def get_stripesize(self):
        return self._fs.get('stripe_size', None)

    # Target status setters
    #
    def register_clients(self, nodes):
        """
        Call the file system new client registration function for each
        nodes given as parameters.
        Parameters:
        @type nodes: List
        @param nodes : list of nodes to register as new file system client
        """
        for node in nodes:
            self._fs.register_client(node)

    def unregister_clients(self, nodes):
        """
        Call the file system client unregistration function for each
        nodes given as parameters.
        Parameters:
        @type nodes: List
        @param nodes : list of nodes to unregister from file system client list
        """
        for node in nodes:
            self._fs.unregister_client(node)

    def set_status_clients_mount_complete(self, nodes, options=None):
        for node in nodes:
            self._fs.set_status_client_mount_complete(node, options)

    def set_status_clients_mount_failed(self, nodes, options=None):
        for node in nodes:
            self._fs.set_status_client_mount_failed(node, options)

    def set_status_clients_mount_warning(self, nodes, options=None):
        for node in nodes:
            self._fs.set_status_client_mount_warning(node, options)

    def set_status_clients_umount_complete(self, nodes, options=None):
        for node in nodes:
            self._fs.set_status_client_umount_complete(node, options)

    def set_status_clients_umount_failed(self, nodes, options=None):
        for node in nodes:
            self._fs.set_status_client_umount_failed(node, options)

    def set_status_clients_umount_warning(self, nodes, options=None):
        for node in nodes:
            self._fs.set_status_client_umount_warning(node, options)

    def set_debug(self, debug):
        self.debug = debug

    def set_status_targets_unknown(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to UNKNOWN
        """
        for target in targets:
            self._fs.set_status_target_unknown(target, options)
            
    def set_status_targets_ko(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to KO
        """
        for target in targets:
            self._fs.set_status_target_ko(target, options)
         
    def set_status_targets_available(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to AVAILABLE
        """
        for target in targets:
            self._fs.set_status_target_available(target, options)

    def set_status_targets_formating(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to FORMATING
        """
        for target in targets:
            self._fs.set_status_target_formating(target, options)

    def set_status_targets_format_failed(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to FORMAT_FAILED
        """
        for target in targets:
            self._fs.set_status_target_format_failed(target, options)

    def set_status_targets_formated(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to FORMATED
        """
        for target in targets:
            self._fs.set_status_target_formated(target, options)

    def set_status_targets_offline(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to OFFLINE
        """
        for target in targets:
            self._fs.set_status_target_offline(target, options)

    def set_status_targets_starting(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to STARTING
        """
        for target in targets:
            self._fs.set_status_target_starting(target, options)

    def set_status_targets_online(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to ONLINE
        """
        for target in targets:
            self._fs.set_status_target_online(target, options)

    def set_status_targets_critical(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to CRITICAL
        """
        for target in targets:
            self._fs.set_status_target_critical(target, options)

    def set_status_targets_stopping(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to STOPPING
        """
        for target in targets:
            self._fs.set_status_target_stopping(target, options)

    def set_status_targets_unreachable(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to UNREACHABLE
        """
        for target in targets:
            self._fs.set_status_target_unreachable(target, options)
            
    def set_status_targets_checking(self, targets, options=None):
        """
        This function is used to set the status of specified targets
        to CHECKING
        """
        for target in targets:
            self._fs.set_status_target_checking(target, options)
            
    def get_status_clients(self):
        """
        This function returns the status of each clients
        using the current file system.
        """
        return self._fs.get_status_clients()

    def register_fs(self):
        """
        This function aims to register the file system configuration
        to the backend.
        """
        self._fs.register()

    def unregister_fs(self):
        """
        This function aims to unregister the file system configuration
        from the backend.
        """
        self._fs.unregister()

    def set_status_fs_installed(self, options=None):
        """
        This function is used to set the status of current file system
        to INSTALLED
        """
        self._fs.set_status_installed(options)

    def set_status_fs_format_failed(self, options=None):
        """
        This function is used to set the status of current file system
        to FORMAT_FAILED
        """
        self._fs.set_status_format_failed(options)

    def set_status_fs_formating(self, options=None):
        """
        This function is used to set the status of current file system
        to FORMATING
        """
        self._fs.set_status_formating(options)

    def set_status_fs_formated(self, options=None):
        """
        This function is used to set the status of current file system
        to FORMATED
        """
        self._fs.set_status_formated(options)

    def set_status_fs_starting(self, options=None):
        """
        This function is used to set the status of current file system
        to STARTING
        """
        self._fs.set_status_starting(options)

    def set_status_fs_online(self, options=None):
        """
        This function is used to set the status of current file system
        to ONLINE
        """
        self._fs.set_status_online(options)

    def set_status_fs_mounted(self, options=None):
        """
        This function is used to set the status of current file system
        to MOUNTED
        """
        self._fs.set_status_mounted(options)

    def set_status_fs_stopping(self, options=None):
        """
        This function is used to set the status of current file system
        to STOPPING
        """
        self._fs.set_status_stopping(options)

    def set_status_fs_offline(self, options=None):
        """
        This function is used to set the status of current file system
        to OFFLINE
        """
        self._fs.set_status_offline(options)

    def set_status_fs_checking(self, options=None):
        """
        This function is used to set the status of current file system
        to CHECKING
        """
        self._fs.set_status_checking(options)

    def set_status_fs_unknown(self, options=None):
        """
        This function is used to set the status of current file system
        to UNKNOWN
        """
        self._fs.set_status_unknown(options)

    def set_status_fs_warning(self, options=None):
        """
        This function is used to set the status of current file system
        to WARNING
        """
        self._fs.set_status_warning(options)

    def set_status_fs_critical(self, options=None):
        """
        This function is used to set the status of current file system
        to CRITICAL
        """
        self._fs.set_status_critical(options)

    def set_status_fs_online_failed(self, options=None):
        """
        This function is used to set the status of current file system
        to ONLINE_FAILED
        """
        self._fs.set_status_online_failed(options)

    def set_status_fs_offline_failed(self, options=None):
        """
        This function is used to set the status of current file system
        to OFFLINE_FAILED
        """
        self._fs.set_status_offline_failed(options)

    def get_status_fs(self):
        """
        This function returns the status of current file system.
        """
        return self._fs.get_status()

