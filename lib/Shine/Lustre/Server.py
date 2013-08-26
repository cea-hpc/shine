# Server.py -- Lustre Server base class
# Copyright (C) 2007-2013 CEA
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
Lustre server management.
"""

import socket

from ClusterShell.Task import task_self, NodeSet

from Shine.Lustre import ServerError
from Shine.Lustre.Actions.Modules import LoadModules, UnloadModules

class ServerGroup(object):
    """
    List of Server instance, with helpers to filter of display them.
    """

    def __init__(self, iterable=None):
        self._list = []
        if iterable is not None:
            self._list = list(iterable)

    def __len__(self):
        return len(self._list)

    def __getitem__(self, index):
        return self._list[index]

    def __iter__(self):
        return iter(self._list)

    def append(self, server):
        """Append the provided server at the end of group."""
        self._list.append(server)

    def select(self, nodeset):
        """
        Return a ServerGroup containing only server which hostname are 
        present in provided nodeset.
        """
        return ServerGroup((srv for srv in self if srv.hostname in nodeset))

    def distant(self):
        """Return a new ServerGroup with only distant servers."""
        return ServerGroup((srv for srv in self if not srv.is_local()))

    def nodeset(self):
        """Return a NodeSet from server hostnames."""
        return NodeSet.fromlist((srv.hostname for srv in self))


class Server(object):
    """
    Represents a node in the cluster, by its hostname and NIDs.

    Currently, it is link to no specific filesystem nor components.
    """

    _CACHE_HOSTNAME_SHORT = None
    _CACHE_HOSTNAME_LONG = None

    def __init__(self, hostname, nids):
        assert type(nids) is list
        self.nids = nids
        self.hostname = NodeSet(hostname)
        self.modules = dict()

    def __str__(self):
        return "%s (%s)" % (self.hostname, ','.join(self.nids))

    @classmethod
    def hostname_long(cls):
        """
        Return cached long host name. If not already cached, resolve and cache
        it.
        """
        if not cls._CACHE_HOSTNAME_LONG:
            cls._CACHE_HOSTNAME_LONG = socket.getfqdn()
        return cls._CACHE_HOSTNAME_LONG
        
    @classmethod
    def hostname_short(cls):
        """
        Return cached short host name. If not already cached, resolve and cache
        it.
        """
        if not cls._CACHE_HOSTNAME_SHORT:
            cls._CACHE_HOSTNAME_SHORT = cls.hostname_long().split('.', 1)[0]
        return cls._CACHE_HOSTNAME_SHORT
 
    @classmethod
    def distant_servers(cls, servers):
        """
        Filter the local host from the provided server list.
        """
        if cls.hostname_long() in servers:
            return servers.difference(cls.hostname_long())
        elif cls.hostname_short() in servers:
            return servers.difference(cls.hostname_short())
        else:
            return servers

    def is_local(self):
        """
        Return true if the node where this code is running matches the server 
        node_name.
        This means node_name should either match the machine fully qualified
        domain name or machine short-name.
        """
        srvname = str(self.hostname)
        return srvname in (self.hostname_long(), self.hostname_short())

    def raise_if_mod_in_use(self):
        """Raise a ServerError if Lustre modules are currently in use."""
        if self.modules.get('lustre', 0) > 0:
            raise ServerError(self, "Lustre modules are busy")

    def lustre_check(self):
        """
        Verify server Lustre sanity.

        It analyzes which Lustre module is loaded and keeps it in self.modules
        """
        self.modules.clear()
        try:
            modlist = open('/proc/modules')
            for line in modlist:
                modname, _, count, _ = line.split(' ', 3)
                if modname in ('libcfs', 'lustre', 'ldiskfs'):
                    self.modules[modname] = int(count)
        finally:
            modlist.close()

    #
    # Actions
    #

    def tune(self, tuning_model, types, fs_name):
        """
        Tune server parameters.
        """
        task = task_self()

        # Retrieve the list of tuning parameters that must be applied to
        # the current node
        tuning_parameters = tuning_model.get_params_for_name(
                                                    str(self.hostname), types)
        
        # Walk through the tuning parameters list and apply each one of them
        for tuning_parameter in tuning_parameters:
            # Build the command which must be executed on this node to
            # tune de file system.
            command_list = tuning_parameter.build_tuning_command(fs_name)
            
            # Walk through the list of commands created for this parameters
            # and create a shell for each one of them.
            for command in command_list:
                task.shell(command)

    def load_modules(self, **kwargs):
        """Load lustre kernel modules."""
        return LoadModules(self, **kwargs)

    def unload_modules(self, **kwargs):
        """Unload all lustre kernel modules."""
        return UnloadModules(self, **kwargs)
