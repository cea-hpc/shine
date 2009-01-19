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

from ClusterShell.NodeSet import NodeSet

class ConfigException(Exception):
    pass

class Target:
    def __init__(self, type, cf_target):
        self.type = type
        self.dic = cf_target.get_dict()

    def get_type(self):
        return self.type

    def get_tag(self):
        return self.dic.get('tag')
        
    def get_nodename(self):
        return self.dic.get('node')

    def get_dev(self):
        return self.dic.get('dev')

    def get_dev_size(self):
        return self.dic.get('size')

    def get_jdev(self):
        return self.dic.get('jdev')

    def get_jdev_size(self):
        return self.dic.get('jsize')
    

class Clients:
    def __init__(self, cf_client):
        self.dic = cf_client.get_dict()

    def get_nodes(self):
        return self.dic.get('node')

    def get_path(self):
        return self.dic.get('path')
        

class Configuration:
    def __init__(self, fs_name=None, lmf=None):
        """FS configuration initializer."""

        self.debug = False

        # Initialize FS configuration
        if fs_name or lmf:
            try:
                self._fs = FileSystem(fs_name, lmf)
            except ConfigException, e:
                raise ConfigException("Error during parsing of filesystem configuration file : %s" % e) 
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

    def get_client_nodes(self):
        nodes = NodeSet()
        if self._fs.has_key('client'):
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
        cli_cf_list = self._fs.get('client')
        # build a dict where keys are mount paths
        mounts = {}
        default_path = self._fs.get_one('mount_path')

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
                path = clients.get_path()
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
        return self._fs.get_one('mount_path')


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

    def set_debug(self, debug):
        self.debug = debug

    def get_status_clients(self):
        return self._fs.get_status_clients()

        
