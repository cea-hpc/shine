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

from ModelFile import ModelFile, SubElement

import re

class Model(ModelFile):

    syntax = { 
       'fs_name'            : 'string',
       'stripe_size'        : 'digit',
       'stripe_count'       : 'digit',
       'stripe_pattern'     : [ '0' ],
       'nettype'            : [ 'elan', 'tcp', 'o2ib'],
       'fstype'             : [ 'ldiskfs', 'ext3' ],
       'failover'           : [ 'yes', 'no' ],
       'ha_timeout'         : 'digit',
       'lustre_upcall'      : 'path',
       'portals_upcall'     : 'path',
       'mdt_mkfs_options'   : 'string',
       'mdt_inode_size'     : 'digit',
       'mdt_mount_options'  : 'string',
       'ost_mkfs_options'   : 'string',
       'ost_inode_size'     : 'digit',
       'ost_mount_options'  : 'string',
       'cluster_id'         : 'digit',
       'quota'              : ['yes', 'no'],
       'quota_options'      : 'string',
       'description'        : 'string',
       'mount_options'      : 'string',
       'mount_path'         : 'path',

       'mgt'                : 'subelem',
       'mdt'                : 'subelem',
       'ost'                : 'subelem'
       }

    def sub_element(self, key, value):
        return ModelDevice(key, value)
    
    def _keycmp(self, k1, k2):
        """ sort()-compliant compare function for nice xmf keys sorting.
        """
        target_keys = [ 'mgt', 'mdt', 'ost' ]

        k1_is_target = k2_is_target = 0

        # Check if keys are target keys
        if k1 in target_keys:
            k1_is_target = 1
        if k2 in target_keys:
            k2_is_target = 1
        # Put target keys at the end of the file
        if k1_is_target and not k2_is_target:
            return 1
        elif not k1_is_target and k2_is_target:
            return -1
        # If both are targets, sort them by index so that the mgt will be the first
        elif k1_is_target and k2_is_target:
            return cmp(target_keys.index(k1), target_keys.index(k2))
        else:
            # Otherwise, call the default compare function.
            return cmp(k1, k2)
    
class ModelDevice(SubElement):

    syntax = {
      'name'       : 'string',
      'node_name'  : 'string',
      'dev'        : 'string',
      'jdev'       : 'string',
      'size'       : 'string',
      'jsize'      : 'string',
      'cfg_status' : ['available', 'formated']
    }

    def match_device(self, candidates):
        matching = []

        # Foreach possible target
        for target in candidates:

            # Verify my keys matches its attributes
            for key, regexp in self:
                # FIXME: Ugh! not very beautiful
                try:
                    pattern = target.get(key)
                    # FIXME: Manage the possible regexp exception
                    if not re.match('^' + regexp + '$', pattern):
                        break
                except KeyError:
                    pass
            else:
                matching.append(target)

        return matching

    
