# Globals.py -- Configuration of global parameters
# Copyright (C) 2007-2015 CEA
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
Classes used to manipulate Shine global configuration file.

This is mostly done using the Globals singleton.
"""

import os

from Shine.Configuration.ModelFile import ModelFile, SimpleElement


class Globals(object):
    """
    Global paramaters configuration class.
    Design Pattern: Singleton
    """
    __instance = None

    DEFAULT_CONF_FILE = "/etc/shine/shine.conf"

    def __new__(cls):
        if not Globals.__instance:
            Globals.__instance = Globals._Globals()
            # Load config file
            if os.path.exists(cls.DEFAULT_CONF_FILE):
                Globals.__instance.load(cls.DEFAULT_CONF_FILE)
        return Globals.__instance

    def __getattr__(self, attr):
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, val):
        return setattr(self.__instance, attr, val)


    class _Globals(ModelFile):

        def __init__(self, sep="=", linesep="\n"):
            ModelFile.__init__(self, sep, linesep)

            # Backend stuff
            self.add_element('backend',             check='enum',
                    default='None', values=['ClusterDB', 'File', 'None'])
            self.add_element('storage_file',        check='path',
                    default='/etc/shine/storage.conf')
            self.add_element('status_dir',          check='path',
                    default='/var/cache/shine/status')

            # Config dirs
            self.add_element('conf_dir',            check='path',
                    default='/var/cache/shine/conf')
            self.add_element('lmf_dir',             check='path',
                    default='/etc/shine/models')

            # Optional config files
            self.add_element('tuning_file',         check='path')
            self.add_element('lnet_conf',           check='path')

            # Timeouts
            self.add_element('ssh_connect_timeout', check='digit',
                    default=30)
            self.add_element('ssh_fanout',          check='digit',
                    default=0)
            self.add_element('default_timeout',     check='digit',
                    default=30)

            # Commands
            self.add_element('command_path',        check='path')

            # Lustre version
            self.add_element('lustre_version',      check='string')

            # CLI
            self.add_element('color',               check='enum',
                    default='auto', values=['never', 'always', 'auto'])

            # TO BE IMPLEMENTED
            self.add_element('start_timeout',       check='digit')
            self.add_element('mount_timeout',       check='digit')
            self.add_element('stop_timeout',        check='digit')
            self.add_element('status_timeout',      check='digit')
            self.add_element('log_file',            check='path')
            self.add_element('log_level',           check='string')

        def add_element(self, name, multiple=False, fold=False, **kwargs):
            """
            For this class, all elements are replaced by the local
            DefaultElement class.

            Only for convenience.
            """
            self.add_custom(name, DefaultElement(**kwargs), multiple, fold)

        def lustre_version_is_smaller(self, version):
            """
            Return true if the Lustre version defined in configuration
            is smaller than the one provided.
            If no version is speficied in configuration, it always returns
            False.
            """
            if 'lustre_version' in self:
                return self['lustre_version'].split('.') < version.split('.')
            else:
                return False

        def get_backend(self):
            return self.get('backend')

        def get_storage_file(self):
            return self.get('storage_file')

        def get_status_dir(self):
            return self.get('status_dir')

        def get_conf_dir(self):
            return self.get('conf_dir')

        def get_lmf_dir(self):
            return self.get('lmf_dir')

        def get_tuning_file(self):
            return self.get('tuning_file')

        def get_ssh_connect_timeout(self):
            return self.get('ssh_connect_timeout')

        def get_ssh_fanout(self):
            return self.get('ssh_fanout')


class DefaultElement(SimpleElement):
    """
    SimpleElement with a special handling of default value.

    Currently, SimpleElement does return the default value only when get() is
    called. As I'm not sure it is a good idea to modify the global behaviour,
    this class is here to fix this only for Globals().
    """

    def __iter__(self):
        yield self.get()

    def __str__(self):
        return str(self.get())

    def __len__(self):
        return int(self.get() is not None)
