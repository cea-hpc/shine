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
# ost: tag=ost1_cors115 node=cors115 dev=/dev/cciss/c0d3 size=71126640 index=3
#

class TargetDevice:
    """ Objet representation of a target (mgt, mdt, ost) device (/dev/stuff)
    """
    def __init__(self, target, dic):
        self.target = target
        self.dict = copy.copy(dic)

    def get(self, key):
        return self.dict[key]

    def getline(self):
        line = ""
        for k, v in self.dict.iteritems():
            line += "%s=%s " % (k, v)
        return line.strip()

    def __str__(self):
        # mandatory
        node = self.dict['node']
        dev = self.dict['dev']
        # optional
        tag = self.dict.get('tag', '')
        size = self.dict.get('size', 0)
        jdev = self.dict.get('jdev', '')
        jsize = self.dict.get('jsize', 0)
        return "%s on %s (dev=%s, size=%lu, jdev=%s, jsize=%lu)" % (tag, node, dev, size, jdev, jsize)

