# FSUtils.py -- Useful shine FS utility functions
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


from Configuration.Configuration import Configuration
from Lustre.FileSystem import FileSystem
from Lustre.Server import *
from Lustre.Target import *

from ClusterShell.NodeSet import NodeSet, RangeSet

import socket

def instantiate_lustrefs(fs_conf, target_types=None, nodes=None, excluded=None,
        failover_node=None, indexes=None, labels=None, groups=None,
        event_handler=None):
    """
    Instantiate shine Lustre filesystem classes from configuration.
    """
    # Arguments interpretation
    assert indexes is None or isinstance(indexes, RangeSet)
    assert labels is None or isinstance(labels, NodeSet)

    # Create file system instance
    fs = FileSystem(fs_conf.get_fs_name(), event_handler)

    servers = {}

    # Create attached file system targets...
    for cf_target in fs_conf.iter_targets():
        target_node = cf_target.get_nodename()

        server = servers.setdefault(target_node, Server(target_node, fs_conf.get_nid(target_node)))

        # retrieve config variables
        cf_t_type = cf_target.get_type()
        cf_t_mode = cf_target.get_mode()
        cf_t_index = cf_target.get_index()
        cf_t_dev = cf_target.get_dev()
        cf_t_jdev = cf_target.get_jdev()
        cf_t_group = cf_target.get_group()
        cf_t_tag = cf_target.get_tag()

        # filter on target types, indexes, groups and nodes
        target_action_enabled = True
        if (target_types is not None and cf_t_type not in target_types) or \
            (indexes is not None and cf_t_index not in indexes) or \
            (groups is not None and (cf_t_group is None or cf_t_group not in groups)) or \
            (nodes is not None and server not in nodes) or \
            (excluded is not None and server in excluded):
                target_action_enabled = False

        target = fs.new_target(server, cf_t_type, cf_t_index, cf_t_dev, cf_t_jdev,
                cf_t_group, cf_t_tag, target_action_enabled, cf_t_mode)

        # Now the device is instanciated, we could check label name
        if (labels is not None and target.label not in labels):
            target.action_enabled = False

        # add failover hosts
        ha_nodes = cf_target.ha_nodes()
        for ha_node in cf_target.ha_nodes():
            target.add_server(Server(ha_node, fs_conf.get_nid(ha_node)))

    # Create attached file system clients...
    for client_node, mount_path in fs_conf.iter_clients():
        server = servers.setdefault(client_node, Server(client_node, fs_conf.get_nid(client_node)))

        # filter on nodes
        client_action_enabled = True
        if (nodes is not None and server not in nodes) or \
            (excluded is not None and server in excluded) or \
            (labels is not None):
            client_action_enabled = False
        # if a target is specified, no client enabled
        if target_types is not None:
            client_action_enabled = False

        client = fs.new_client(server, mount_path, client_action_enabled)

    return fs


def create_lustrefs(fs_model_file, event_handler=None, nodes=None, excluded=None):
    """
    """
    fs_conf = Configuration(fs_model=fs_model_file)
    
    fs = instantiate_lustrefs(fs_conf, event_handler=event_handler, \
                              nodes=nodes, excluded=excluded)

    # Register file system configuration to the backend
    fs_conf.register_fs()

    return fs_conf, fs


def open_lustrefs(fs_name, target_types=None, nodes=None, excluded=None,
          failover_node=None, indexes=None, labels=None, groups=None,
          event_handler=None):
    """
    Helper function used to build an instantiated Lustre.FileSystem
    from installed shine configuration.
    """
    # Create file system configuration
    fs_conf = Configuration(fs_name)

    if target_types:
        target_types = target_types.split(',')

    fs = instantiate_lustrefs(fs_conf, target_types, nodes, excluded,
                              failover_node, indexes, labels, groups,
                              event_handler)

    return fs_conf, fs

