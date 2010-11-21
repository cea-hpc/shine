# NidMap.py -- Nid mapping helpers
# Copyright (C) 2008, 2009 CEA
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
Help to manipulate a mapping between a list of nodes and a list of Lustre NID.
"""

from ClusterShell.NodeSet import NodeSet
from Shine.Configuration.Exceptions import ConfigException

class InvalidNidMapError(ConfigException):
    """Raise when nodes or nid ranges are used"""

    def __init__(self, nodes, nids):
        ConfigException.__init__(self, "Erroneous NID map")
        self.nodes = nodes
        self.nids = nids

    def __str__(self):
        return "Erroneous NID map : %s -> %s" % (self.nodes, self.nids)


class NidMap(object):
    """
    NID mapping helper class for shine.
    """
    def __init__(self, nodes_pat=None, nids_pat=None):
        self._map = {}

        if nodes_pat or nids_pat:
            self.add(nodes_pat, nids_pat)

    def __str__(self):
        output = []
        for nodes, nids in self._map.iteritems():
            output.append("%s -> %s\n" % (nodes, ':'.join(nids)))
        return ''.join(output)

    def __getitem__(self, key):
        return self._map[key]

    def add(self, nodes, nids):
        """
        Add one-to-one mapping from 2 strings representing NodeSet.
        Sizes of the provided nodeset and nidset must be the same.
        """

        # Convert to NodeSets
        ns_nodes, ns_nids = NodeSet(nodes), NodeSet(nids)

        # Sanity check
        if len(ns_nodes) != len(ns_nids):
            raise InvalidNidMapError(ns_nodes, ns_nids)

        # Fill map dict
        for node, nid in zip(ns_nodes, ns_nids):
            self._map.setdefault(node, []).append(nid)

    def add_modelnidmap(self, modelnidmap):
        """
        Add one-to-one mapping from an nidmap line entry as ModelNidMap.
        """

        # Get nodes and nids from the ModelNidMap object representing
        # one nid_map: line
        nodes = modelnidmap.get('nodes')
        nids = modelnidmap.get('nids')

        self.add(nodes, nids)

    @classmethod
    def fromlist(cls, maplist):
        """
        Helper class method to build a NidMap object from a list of
        ModelNidMap objects as provided by Shine.Configuration.Model
        """
        nidmap = NidMap()
        for elem in maplist:
            nidmap.add_modelnidmap(elem)
        return nidmap
