# Configuration.py -- Configuration container
# Copyright (C) 2007-2014 CEA
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

from ClusterShell.NodeSet import NodeSet

from Shine.Configuration.FileSystem import FileSystem, Target, Routers, Clients
from Shine.Configuration.FileSystem import DeviceRunAction
from Shine.Configuration.Exceptions import ConfigException


class Configuration:
    def __init__(self):
        """FS configuration initializer."""
        self.debug = False
        self._fs = None

    @classmethod
    def load_from_cache(cls, fsname):
        conf = Configuration()
        conf._fs = FileSystem.load_from_fsname(fsname)
        return conf

    @classmethod
    def load_from_model(cls, lmf):
        conf = Configuration()
        conf._fs = FileSystem(lmf)
        return conf

    @classmethod
    def create_from_model(cls, lmf, update_mode=False):
        conf = Configuration()
        conf._fs = FileSystem.create_from_model(lmf, update_mode=update_mode)
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
            if target_type not in self._fs.model:
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

    def get_default_mount_path(self):
        """
        Return the default client mount path or raise a ConfigException 
        if it does not exist.
        """
        if not 'mount_path' in self._fs.model:
            raise ConfigException("mount_path not specified")
        return self._fs.get('mount_path')

    def iter_clients(self):
        """
        Iterate over (node, mount_path, mount_options, subdir)
        """
        if not 'client' in self._fs.model:
            return

        for clnt in [Clients(clnt) for clnt in self._fs.get('client')]:
            assert '[' not in clnt.get_nodes()
            path = clnt.get_mount_path() or self.get_default_mount_path()
            opts = clnt.get_mount_options() or self.get_default_mount_options()
            subdir = clnt.get('subdir')
            yield clnt.get_nodes(), path, opts, subdir

    def iter_routers(self):
        """
        Iterate over (node)
        """
        if 'router' in self._fs.model:
            for elem in self._fs.get('router'):
                rtr = Routers(elem)
                yield rtr.get_nodes()

    # General FS getters
    #
    def get_fs_name(self):
        return self._fs.get('fs_name')

    def get_cfg_filename(self):
        """
        Return FS xmf file path.
        """
        return self._fs.xmf_path

    def get_description(self):
        return self._fs.get('description')

    def has_quota(self):
        """
        Return if quota has been enabled in the configuration file.
        """
        return self._fs.get('quota')

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

    def get_default_mount_options(self):
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

    def get_dev_action(self, alias):
        dev_acts = self._fs.get('dev_action')
        for act in dev_acts:
            if act['alias'] == alias:
                return DeviceRunAction(act)
        raise KeyError('dev_action "%s" not found' % alias)

    # Target status setters
    #
    def register_targets(self, targets=None):
        """
        Set filesystem targets as 'in use'.

        If `targets' is not specified, all managed targets from the
        filesystem will be used.

        These targets could not be use anymore for other filesystems.
        """
        if not targets:
            targets = []
            for tgttype in ('mgt', 'mdt', 'ost'):
                if tgttype not in self._fs.model:
                    continue
                for target in self._fs.get(tgttype):
                    if target.get('mode') == 'managed':
                        targets.append(Target(tgttype, target))

        for target in targets:
            self._fs.register_target(target)

    def unregister_targets(self, targets=None):
        """
        Set filesystem targets as available in the backend.

        If `targets' is not specified, all managed targets from the
        filesystem will be used.

        These targets could be now reuse.
        """
        if not targets:
            targets = []
            for tgttype in ('mgt', 'mdt', 'ost'):
                if tgttype not in self._fs.model:
                    continue
                for target in self._fs.get(tgttype):
                    if target.get('mode') == 'managed':
                        targets.append(Target(tgttype, target))

        for target in targets:
            self._fs.unregister_target(target)

    def set_debug(self, debug):
        self.debug = debug

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
