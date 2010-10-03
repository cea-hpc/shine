# TargetDevice.py -- Representation of a Target Device
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


import copy

#
# ost: tag=ost1_cors115 node=cors115 dev=/dev/cciss/c0d3 index=3
#

class TargetDevice:
    """ Objet representation of a target (mgt, mdt, ost) device (/dev/stuff)
    """
    def __init__(self, target, dic):
        self.target = target
        self.params = copy.copy(dic)

    def get(self, key):
        return self.params.get(key)

    def getline(self):
        line = ""
        for k, v in self.params.iteritems():
            if type(v) is list:
                for lv in v:
                    line += "%s=%s " % (k, lv)
            else:
                line += "%s=%s " % (k, v)
        return line.strip()

    def has_index(self):
        return self.params.has_key('index')
    
    def add_index(self, index):
        self.params['index'] = index

    def index(self):
        return int(self.params['index'])

    def __str__(self):
        node = self.params.get('node', '')
        ha_node = self.params.get('ha_node')
        if not ha_node:
            ha_node = ""
        else:
            ha_node = ",%s" % ",".join(ha_node)
        index = self.params.get('index', 'AUTO')
        tag = self.params.get('tag', '')
        dev = self.params.get('dev', '')
        jdev = self.params.get('jdev', '')
        if jdev:
            jdev = "jdev=%s, " % jdev
        group = self.params.get('group', '')
        if group:
            group = ", group=%s" % group
        return "%s on %s%s tag=\"%s\" (%sindex=%s%s)" % \
                (dev, node, ha_node, tag, jdev, index, group)

