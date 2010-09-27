# Copyright (C) 2007, 2008, 2009 CEA
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
       'mgt_mkfs_options'   : 'string',
       'mgt_mount_options'  : 'string',
       'mgt_mount_path'     : 'string',
       'mgt_format_params'  : 'string',
       'mdt_mkfs_options'   : 'string',
       'mdt_mount_options'  : 'string',
       'mdt_mount_path'     : 'string',
       'mdt_format_params'  : 'string',
       'ost_mkfs_options'   : 'string',
       'ost_mount_options'  : 'string',
       'ost_mount_path'     : 'string',
       'ost_format_params'  : 'string',
       'quota'              : ['yes', 'no'],
       'quota_type'         : 'string',
       'quota_bunit'        : 'digit',
       'quota_iunit'        : 'digit',
       'quota_btune'        : 'digit',
       'quota_itune'        : 'digit',
       'description'        : 'string',
       'mount_options'      : 'string',
       'mount_path'         : 'path',

       'nid_map'            : 'subelem',

       'mgt'                : 'subelem',
       'mdt'                : 'subelem',
       'ost'                : 'subelem',
       'client'             : 'subelem',
       'router'             : 'subelem'
       }

    defaults = {
       'stripe_size'        : 1048576,
       'stripe_count'       : 1,
       'mgt_mkfs_options'   : "",
       'mgt_mount_options'  : "",
       'mgt_mount_path'     : "/mnt/$fs_name/mgt",
       'mgt_format_params'  : "",
       'mdt_mkfs_options'   : "",
       'mdt_mount_options'  : "",
       'mdt_mount_path'     : "/mnt/$fs_name/mdt/$index",
       'mdt_format_params'  : "",
       'ost_mkfs_options'   : "",
       'ost_mount_options'  : "",
       'ost_mount_path'     : "/mnt/$fs_name/ost/$index",
       'ost_format_params'  : "",
       'quota_type'         : "ug"
       }

    def sub_element(self, key, value):
        if key == 'nid_map':
            return ModelNidMap(self, value)
        elif key == 'client':
            return self.sub_element_expand(ModelClient, key, value)
        else:
            # targets
            return self.sub_element_expand(ModelDevice, key, value)
    
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
    """
    SubElement representing a target (mgt, mdt, ost) configuration
    line.
    """

    syntax = {
      'tag'        : 'string',
      'node'       : 'string',
      'ha_node'    : 'string',
      'dev'        : 'string',
      'jdev'       : 'string',
      'index'      : 'digit',
      'group'      : 'string',
      'mode'       : 'string',
      'network'    : 'string',
    }

    defaults = {
      'mode'       : 'managed'
    }


    def match_device(self, candidates):
        matching = []

        # Foreach possible target
        for target in candidates:

            # Verify my keys matches its attributes
            for key, regexp in self:
                pattern = target.get(key)
                if pattern is None:
                    break
                # FIXME: Manage the possible regexp exception
                if not re.match('^' + regexp + '$', pattern):
                    break
            else:
                matching.append(target)

        return matching

    
class ModelNidMap(SubElement):
    """SubElement representing a nid_map configuration line."""

    syntax = {
      'nodes'       : 'string',
      'nids'        : 'string'
    }

    def __str__(self):    
        """
        Sort nodes and nids keys for a better understanding.
        """
        keys = set(self.keys.keys())
        elems = []
        for k in ('nodes','nids'):
            elems.append("%s%s%s" % (k, self.sep, self.get_one(k)))
            keys.remove(k)
        for k in keys:
            elems.append("%s%s%s" % (k, self.sep, self.get_one(k)))
        return ' '.join(elems)


class ModelClient(SubElement):
    """SubElement representing a client configuration line."""
    
    syntax = {
      'node'       : 'string',
      'mount_path' : 'string'
    }

class ModelRouteur(SubElement):
    """SubElement representing a routeur configuration line."""

    syntax = {
      'node'       : 'string',
    }
