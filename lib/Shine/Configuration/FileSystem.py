# FileSystem.py -- Lustre file system configuration
# Copyright (C) 2007, 2008 CEA
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
    def create_from_model(cls, lmf):
        """Save to cache."""
        model = FileSystem(lmf)
        # xmf_path could be set later if setup_target_devices do not need it
        model.xmf_path = cls._cache_path(model.fs_name)
        # This will create the XMF 
        model._setup_target_devices()

        # Reload from content saved in _setup_target_devices()
        return cls.load_from_fsname(model.fs_name)

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

    def _setup_target_devices(self):
        """ Generate the eXtended Model File XMF
        """
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
                candidates = self.backend.get_target_devices(target)

                # Save the model target selection
                target_models = copy.copy(self.model.get(target))

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

        # Save XMF
        self.model.save(self.xmf_path,
                  "# Shine Lustre file system config file for %s" % \
                  self.fs_name)

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
        """Compare the FileSystem model with another FileSystem and 
        return a dictionnary describing the needed actions."""
        
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
            actions['unmount'] = removed.elements('client')
        if 'client' in added:
            actions['mount'] = added.elements('client')
        if 'client' in changed:
            assert True, 'Client change is not supported'

        # Router has changed
        if 'router' in removed:
            actions.setdefault('stop', []).append(removed.elements('router'))
        if 'router' in added:
            actions.setdefault('start', []).append(added.elements('router'))
        if 'router' in changed:
            assert True, 'Router change is not supported'

        # Some targets have changed
        for tgt in [ 'mgt', 'mdt', 'ost']:
            if tgt in removed:
                actions.setdefault('stop', []).append(removed.elements(tgt))
            if tgt in added:
                actions.setdefault('format', []).append(added.elements(tgt))
                actions.setdefault('start', []).append(added.elements(tgt))
            if tgt in changed:    
                assert True, '%s change is not supported' % tgt.upper()

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

    def register_client(self, node):
        """
        This function aims to register a new client that will be able to mount the
        file system.
        Parameters:
        @type node: string
        @param node : is the new client node name
        """
        if self._start_backend():
            self.backend.register_client(self.fs_name, node)

    def unregister_client(self, node):
        """
        This function aims to unregister a client of this  file system
        Parameters:
        @type node: string
        @param node : is name of the client node to unregister
        """
        if self._start_backend():
            self.backend.unregister_client(self.fs_name, node)

    def _set_status_client(self, node, status, options):
        """
        This function is used to change specified client status.
        """
        if self._start_backend():
            self.backend.set_status_client(self.fs_name, node, status, options)

    def set_status_client_mount_complete(self, node, options):
        """
        This function is used to set the specified client status
        to MOUNT_COMPLETE
        """
        self._set_status_client(node, Backend.MOUNT_COMPLETE, options)

    def set_status_client_mount_failed(self, node, options):
        """
        This function is used to set the specified client status
        to MOUNT_FAILED
        """
        self._set_status_client(node, Backend.MOUNT_FAILED, options)

    def set_status_client_mount_warning(self, node, options):
        """
        This function is used to set the specified client status
        to MOUNT_WARNING
        """
        self._set_status_client(node, Backend.MOUNT_WARNING, options)

    def set_status_client_umount_complete(self, node, options):
        """
        This function is used to set the specified client status
        to UMOUNT_COMPLETE
        """
        self._set_status_client(node, Backend.UMOUNT_COMPLETE, options)

    def set_status_client_umount_failed(self, node, options):
        """
        This function is used to set the specified client status
        to UMOUNT_FAILED
        """
        self._set_status_client(node, Backend.UMOUNT_FAILED, options)

    def set_status_client_umount_warning(self, node, options):
        """
        This function is used to set the specified client status
        to UMOUNT_WARNING
        """
        self._set_status_client(node, Backend.UMOUNT_WARNING, options)

    def get_status_clients(self):
        """
        This function returns the status of each clients
        involved in the current file system.
        """
        if self._start_backend():
            return self.backend.get_status_clients(self.fs_name)
        else:
            # XXX: If no backend, sure we want an empty list?
            return []

    def _set_status_target(self, target, status, options):
        """
        This function is used to change the specified target status.
        """
        if self._start_backend():
            self.backend.set_status_target(self.fs_name, target,
                status, options)

    def set_status_target_unknown(self, target, options):
        """
        This function is used to set the specified target status
        to UNKNOWN
        """
        self._set_status_target(target, Backend.TARGET_UNKNOWN, options)

    def set_status_target_ko(self, target, options):
        """
        This function is used to set the specified target status
        to KO
        """
        self._set_status_target(target, Backend.TARGET_KO, options)

    def set_status_target_available(self, target, options):
        """
        This function is used to set the specified target status
        to AVAILABLE
        """
        # Set the fs_name to Free since these targets are availble
        # which means not used by any file system.
        self._set_status_target(target, Backend.TARGET_AVAILABLE, options)

    def set_status_target_formating(self, target, options):
        """
        This function is used to set the specified target status
        to FORMATING
        """
        self._set_status_target(target, Backend.TARGET_FORMATING, options)

    def set_status_target_format_failed(self, target, options):
        """
        This function is used to set the specified target status
        to FORMAT_FAILED
        """
        self._set_status_target(target, Backend.TARGET_FORMAT_FAILED, options)

    def set_status_target_formated(self, target, options):
        """
        This function is used to set the specified target status
        to FORMATED
        """
        self._set_status_target(target, Backend.TARGET_FORMATED, options)

    def set_status_target_offline(self, target, options):
        """
        This function is used to set the specified target status
        to OFFLINE
        """
        self._set_status_target(target, Backend.TARGET_OFFLINE, options)

    def set_status_target_starting(self, target, options):
        """
        This function is used to set the specified target status
        to STARTING
        """
        self._set_status_target(target, Backend.TARGET_STARTING, options)

    def set_status_target_online(self, target, options):
        """
        This function is used to set the specified target status
        to ONLINE
        """
        self._set_status_target(target, Backend.TARGET_ONLINE, options)

    def set_status_target_critical(self, target, options):
        """
        This function is used to set the specified target status
        to CRITICAL
        """
        self._set_status_target(target, Backend.TARGET_CRITICAL, options)

    def set_status_target_stopping(self, target, options):
        """
        This function is used to set the specified target status
        to STOPPING
        """
        self._set_status_target(target, Backend.TARGET_STOPPING, options)

    def set_status_target_unreachable(self, target, options):
        """
        This function is used to set the specified target status
        to UNREACHABLE
        """
        self._set_status_target(target, Backend.TARGET_UNREACHABLE, options)

    def set_status_target_checking(self, target, options):
        """
        This function is used to set the specified target status
        to CHECKING
        """
        self._set_status_target(target, Backend.TARGET_CHECKING, options)

    def get_status_targets(self):
        """
        This function returns the status of each targets
        involved in the current file system.
        """
        if self._start_backend():
            return self.backend.get_status_targets(self.fs_name)
        else:
            # XXX: If no backend, sure we want an empty list?
            return []

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

