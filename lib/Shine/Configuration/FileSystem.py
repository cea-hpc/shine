# FileSystem.py -- Lustre file system configuration
# Copyright (C) 2007-2012 CEA
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
import os

from ClusterShell.NodeSet import RangeSet

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Model import Model
from Shine.Configuration.Exceptions import ConfigInvalidFileSystem, \
                                           ConfigDeviceNotFoundError, \
                                           ConfigException
from Shine.Configuration.TuningModel import TuningModel
from Shine.Configuration.NidMap import NidMap
from Shine.Configuration.Backend.Backend import Backend
from Shine.Configuration.Backend.BackendRegistry import BackendRegistry


class ModelFileIOError(ConfigException):
    """Malformed or unfound model file or XML file."""

class Target:
    def __init__(self, type, cf_target):
        self.type = type
        self.dic = cf_target.as_dict()

    def get(self, key, default=None):
        return self.dic.get(key, default)

    def get_type(self):
        return self.type

    def get_tag(self):
        return self.dic.get('tag')
        
    def get_nodename(self):
        return self.dic.get('node')

    def ha_nodes(self):
        """
        Return ha_nodes list (failover hosts). An empty list is
        returned when no ha_nodes are provided.
        """
        nodes = self.dic.get('ha_node')
        if not nodes:
            nodes = []
        elif type(nodes) is not list:
            nodes = [nodes]
        return nodes

    def get_dev(self):
        return self.dic.get('dev')

    def get_dev_size(self):
        return self.dic.get('size')

    def get_jdev(self):
        return self.dic.get('jdev')

    def get_jdev_size(self):
        return self.dic.get('jsize')

    def get_index(self):
        return int(self.dic.get('index', 0))

    def get_group(self):
        return self.dic.get('group')
    
    def get_mode(self):
        return self.dic.get('mode', 'managed')

    def get_network(self):
        return self.dic.get('network')

class Clients:
    def __init__(self, cf_client):
        self.dic = cf_client.as_dict()

    def get(self, key, default=None):
        return self.dic.get(key, default)

    def get_nodes(self):
        return self.dic.get('node')

    def get_mount_options(self):
        return self.dic.get('mount_options')

    def get_mount_path(self):
        return self.dic.get('mount_path')

    def get_type(self):
        return 'client'
        

class Routers:
    def __init__(self, cf_router):
        self.dic = cf_router.as_dict()

    def get(self, key, default=None):
        return self.dic.get(key, default)

    def get_nodes(self):
        return self.dic.get('node')

    def get_nodename(self):
        # To be compatible with Target
        return self.get_nodes()

    def get_type(self):
        return 'router'

class FileSystem(object):
    """
    Lustre File System Configuration class.
    """

    def __init__(self, filename):

        self.backend = None
        self.xmf_path = None
        self.model = Model()

        try:
            self.model.load(filename)
        except IOError:
            raise ModelFileIOError("Could not read %s" % filename)

        # Set nodes to nids mapping using the NidMap helper class
        self.nid_map = NidMap.fromlist(self.get('nid_map'))

        # Initialize the tuning model to None if no special tuning configuration
        # is provided
        self.tuning_model = TuningModel()

    @property
    def fs_name(self):
        return self.get('fs_name')

    def get(self, key, default=None):
        """Return the Model value pointed by `key'"""
        return self.model.get(key, default)

    @classmethod
    def _cache_path(cls, fsname):
        """Build and check a cache file path from filesystem name."""
        fs_conf_dir = os.path.expandvars(Globals().get_conf_dir())
        if not os.path.exists(fs_conf_dir):
            raise ConfigException("Cache directory does not exist '%s'" % 
                                  fs_conf_dir)
        return "%s/%s.xmf" % (os.path.normpath(fs_conf_dir), fsname)

    @classmethod
    def create_from_model(cls, lmf, update_mode=False):
        """Save to cache."""
        fsmodel = FileSystem(lmf)
        # xmf_path could be set later if setup_target_devices do not need it
        fsmodel.xmf_path = cls._cache_path(fsmodel.fs_name)
        fsmodel.setup_target_devices(update_mode=update_mode)
        # Save XMF
        fsmodel.model.save(fsmodel.xmf_path,
                  "# Shine Lustre file system config file for %s" % \
                  fsmodel.fs_name)

        # Reload from content saved previously
        return cls.load_from_fsname(fsmodel.fs_name)

    @classmethod
    def load_from_fsname(cls, fsname):
        """Load from cache."""
        conf_file = cls._cache_path(fsname)
        fsconf = FileSystem(conf_file)
        fsconf.xmf_path = conf_file
        return fsconf


    def _start_backend(self):
        """
        Load and start backend subsystem once
        """
        if not self.backend:

            # Start the selected config backend system.
            self.backend = BackendRegistry().get_selected()
            if self.backend:
                self.backend.start()

        return self.backend

    def setup_target_devices(self, update_mode=False):
        """ Generate the eXtended Model File XMF """

        self._start_backend()

        # We have to setup the possible targets, which are: MGT, MDT and OST.
        for target in [ 'mgt', 'mdt', 'ost' ]:

            # So, first, look for which ones are defined in model
            if target not in self.model:
                continue

            # Lustre supports up to FFFF targets per type.
            indexes = RangeSet("0-65535")

            if self.backend:

                # Returns a list of TargetDevices
                fs_name = None
                if update_mode == True:
                    fs_name = self.fs_name
                candidates = self.backend.get_target_devices(target, fs_name=fs_name, update_mode=update_mode)

                # Save the model target selection
                target_models = copy.copy(self.model.get(target))

                # Reduce entropy from backend.
                # (node, dev) should point to a unique device, so this should
                # be enough for sorting. This is not perfect but enough to have
                # a very low entropy in result order.
                candidates.sort(key=lambda x: (x.get('node'), x.get('dev')))

                # Delete it (to be replaced... see below)
                self.model.elements(target).clear()

                try:

                    # Remove already used index from candidate list.
                    for target_model in target_models:
                        if 'index' in target_model:
                            indexes.remove(target_model.get('index'))

                    # Iterates on each Model.Target
                    for target_model in target_models:

                        # Do not try to match external components
                        if target_model.get('mode') == 'external':
                            self.model.elements(target).parse(str(target_model))
                            continue

                        result = target_model.match_device(candidates)
                        if len(result) == 0:
                            raise ConfigDeviceNotFoundError(target_model)

                        for matching in result:
                            candidates.remove(matching)

                            # If an index was specified, set it.
                            if 'index' in target_model:
                                matching.add_index(target_model.get('index'))
                                target_model.elements('index').clear()

                            # Manage index, mandatoy in XMF files
                            if not matching.has_index():
                                matching.add_index(indexes[0])
                                indexes.remove(matching.index())

                            # `matching' is a TargetDevice, we want to add it
                            # to the underlying Model object. The current way
                            # to do this to create a configuration line string
                            # (performed by TargetDevice.getline()) and then
                            # call Model.parse(). 
                            # TODO: add methods to Model/ModelDevice to avoid
                            #  the use of temporary configuration string line.
                            self.model.elements(target).parse(
                                                            matching.getline())

                except KeyError, error:
                    raise ConfigInvalidFileSystem(self, \
                            "Index %d for %s used twice." % \
                            (str(error), target))

            # Support for backend None
            else:

                try:
                    # Remove already used indexes from candidate list.
                    for params in self.model.elements(target):
                        if 'index' in params:
                            indexes.remove(params.get('index'))

                    # Manage index
                    for params in self.model.elements(target):
                        if 'index' not in params:
                            params.add('index', str(indexes[0]))
                            indexes.remove(indexes[0])

                except KeyError, error:
                    raise ConfigInvalidFileSystem(self, \
                             "Index %s for %s used twice." % \
                              (str(error), target))

        self._check_coherency()


    def _check_coherency(self):
        """Verify that the declared components make a coherent filesystem."""

        model = self.model
        # If we have a target or a client, we need a MGT
        if (('client' in model or 'mdt' in model or 'ost' in model) \
            and not ('mgt' in model)):
            raise ConfigInvalidFileSystem(self, "A MGS must be declared.")

        # We should have both MDT and OST or neither
        if ('mdt' in model) ^ ('ost' in model):
            raise ConfigInvalidFileSystem(self,
                     "You must declare both MDT and OST or neither.")

    def compare(self, otherfs):
        """
        Compare the FileSystem model with another FileSystem and return
        a dictionnary describing the needed actions.
        """
        
        actions = {}
        added, changed, removed = self.model.diff(otherfs.model)

        anyset = set(changed.iterkeys()) | set(added.iterkeys()) \
                  | set(removed.iterkeys())

        # Read-only keys: fs_name
        readonly = set(['fs_name'])
        if readonly & anyset:
            raise ConfigException("%s could not be changed" % 
                                  ", ".join(readonly & anyset))

        # Need to reformat targets
        reformatkeys = set(['mgt_mkfs_options', 'mdt_mkfs_options', 
                            'ost_mkfs_options', 'mgt_format_params',
                            'mdt_format_params', 'ost_format_params'])
        if reformatkeys & anyset:
            actions['reformat'] = True

        # Need a tunefs.lustre
        tunefskeys = set(['quota', 'quota_type', 'quota_bunit', 'quota_iunit', 
                          'quota_btune', 'quota_itune', 'stripe_size',
                          'stripe_count'])
        if tunefskeys & anyset:
            actions['tunefs'] = True

        # Need a writeconf
        writeconfkeys = set(['nid_map'])
        if writeconfkeys & anyset:
            # Note: Target removal could also set this flag.
            actions['writeconf'] = True

        # Need to remount clients
        remountkeys = set(['mount_options', 'mount_path'])
        if remountkeys & anyset:
            # XXX: Could be improved to remount only needed clients
            actions['remount'] = True

        # Need to restart targets
        restartkeys = set(['mgt_mount_path', 'mdt_mount_path', 'ost_mount_path',
                           'mgt_mount_options', 'mdt_mount_options', 
                           'ost_mount_options'])
        if restartkeys & anyset:
            actions['restart'] = True

        # Only need to update cache file
        copykeys = set(['description'])
        if copykeys & anyset:
            actions['copyconf'] = True

        # Clients have changed
        if 'client' in removed:
            actions['unmount'] = [ Clients(elem) for elem in removed.elements('client')]
        if 'client' in added:
            actions['mount'] = [ Clients(elem) for elem in added.elements('client')]
        assert 'client' not in changed, 'Client change is not supported'

        # Router has changed
        if 'router' in removed:
            actions.setdefault('stop', []).extend(
                         [Routers(elem) for elem in removed.elements('router')])
        if 'router' in added:
            actions.setdefault('start', []).extend(
                         [Routers(elem) for elem in added.elements('router')])
        assert 'router' not in changed, 'Router change is not supported'

        # Some targets have changed
        for tgt in [ 'mgt', 'mdt', 'ost']:
            if tgt in removed:
                actions['writeconf'] = True
                actions.setdefault('stop', []).extend(
                        [Target(tgt, elem) for elem in removed.elements(tgt)])
            if tgt in added:
                actions.setdefault('format', []).extend(
                        [Target(tgt, elem) for elem in added.elements(tgt)])
                actions.setdefault('start', []).extend(
                        [Target(tgt, elem) for elem in added.elements(tgt)])
            assert tgt not in changed, '%s change is not supported' % tgt.upper()

        # If some actions is required, we need to update config files.
        if len(actions) > 0:
            actions['copyconf'] = True

        return actions

    def get_nid(self, node):
        try:
            return self.nid_map[node]
        except KeyError:
            raise ConfigException("Cannot get NID for %s, aborting. Please verify `nid_map' configuration." % node)

    def close(self):
        if self.backend:
            self.backend.stop()
            self.backend = None

    def register(self):
        """
        This function aims to register the file system configuration
        to the backend.
        """
        if self._start_backend():
            return self.backend.register_fs(self)

    def unregister(self):
        """
        This function aims to remove a file system configuration from
        the backend.
        """
        result = 0
        if self._start_backend():
            result = self.backend.unregister_fs(self)

        if not result:
            os.unlink(self.xmf_path)

        return result

    def register_target(self, target):
        """
        Set the specified target as 'in use'.

        This target could not be use anymore for other filesystems.
        """
        if self._start_backend():
            return self.backend.register_target(self, target)

    def unregister_target(self, target):
        """
        Set the specified target as available in the backend.

        This target could be now reuse.
        """
        if self._start_backend():
            return self.backend.unregister_target(self, target)

    def _set_status(self, status, options):
        """
        This function is used to change the specified filesystem status.
        """
        if self._start_backend():
            self.backend.set_status_fs(self.fs_name, status, options)

    def set_status_installed(self, options):
        """
        This function is used to set the specified filesystem status
        to INSTALLED
        """
        self._set_status(Backend.FS_INSTALLED, options)

    def set_status_formating(self, options):
        """
        This function is used to set the specified filesystem status
        to FORMATING
        """
        self._set_status(Backend.FS_FORMATING, options)

    def set_status_formated(self, options):
        """
        This function is used to set the specified filesystem status
        to FORMATED
        """
        self._set_status(Backend.FS_FORMATED, options)

    def set_status_format_failed(self, options):
        """
        This function is used to set the specified filesystem status
        to FORMAT_FAILED
        """
        self._set_status(Backend.FS_FORMAT_FAILED, options)

    def set_status_starting(self, options):
        """
        This function is used to set the specified filesystem status
        to STARTING
        """
        self._set_status(Backend.FS_STARTING, options)

    def set_status_online(self, options):
        """
        This function is used to set the specified filesystem status
        to ONLINE
        """
        self._set_status(Backend.FS_ONLINE, options)

    def set_status_mounted(self, options):
        """
        This function is used to set the specified filesystem status
        to MOUNTED
        """
        self._set_status(Backend.FS_MOUNTED, options)

    def set_status_stopping(self, options):
        """
        This function is used to set the specified filesystem status
        to STOPPING
        """
        self._set_status(Backend.FS_STOPPING, options)

    def set_status_offline(self, options):
        """
        This function is used to set the specified filesystem status
        to OFFLINE
        """
        self._set_status(Backend.FS_OFFLINE, options)

    def set_status_checking(self, options):
        """
        This function is used to set the specified filesystem status
        to CHECKING
        """
        self._set_status(Backend.FS_CHECKING, options)

    def set_status_unknown(self, options):
        """
        This function is used to set the specified filesystem status
        to UNKNOWN
        """
        self._set_status(Backend.FS_UNKNOWN, options)

    def set_status_warning(self, options):
        """
        This function is used to set the specified filesystem status
        to WARNING
        """
        self._set_status(Backend.FS_WARNING, options)

    def set_status_critical(self, options):
        """
        This function is used to set the specified filesystem status
        to CRITICAL
        """
        self._set_status(Backend.FS_CRITICAL, options)

    def set_status_online_failed(self, options):
        """
        This function is used to set the specified filesystem status
        to ONLINE_FAILED
        """
        self._set_status(Backend.FS_ONLINE_FAILED, options)

    def set_status_offline_failed(self, options):
        """
        This function is used to set the specified filesystem status
        to OFFLINE_FAILED
        """
        self._set_status(Backend.FS_OFFLINE_FAILED, options)

    def get_status(self):
        """
        This function returns the status of the current file system.
        """
        return self.backend.get_status_fs(self.fs_name)

