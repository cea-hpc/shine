# NidMap.py -- Nid mapping helpers
# Copyright (C) 2008 CEA
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


from Exceptions import *

from ClusterShell.NodeSet import NodeSet


class NidMap:
    """
    NID mapping helper class for shine.
    """
    def __init__(self):
        self.map = {}

    def fromlist(cls, l):
        inst = NidMap()

        for map in l:
            inst.add(map)

        return inst
    fromlist = classmethod(fromlist)

    def __str__(self):
        buf = ""
        for k,v in self.map.iteritems():
            buf += "%s -> %s\n" % (k, v)
        return buf

    def __getitem__(self, key):
        return self.map[key]

    def add(self, mapline):
        """
        Add one-to-one mapping from mapline (as string) of the form
        'nodeset nidset'. Sizes of the provided nodeset and nidset
        must be the same.
        """

        # Parse map line
        nodes, nids = mapline.split()

        # Convert to nodesets
        nodes_s, nids_s = NodeSet(nodes), NodeSet(nids)

        # Sanity check
        if len(nodes_s) != len(nids_s):
            raise ConfigBadNidMapError(nodes_s, nids_s)

        # Fill map dict
        nids_l = list(nids_s)
        i = 0
        for node in nodes_s:
            self.map[node] = nids_l[i]
            i = i + 1

