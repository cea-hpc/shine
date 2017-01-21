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

"""
Provides classes to load/read and save Shine model files or cache files.
"""

import re

from Shine.Configuration.ModelFile import ModelFile, SimpleElement, \
                                          MultipleElement, ModelFileValueError

class Model(ModelFile):
    """Represent a Shine model file.

    All method from ModelFile class could be used to manipulate it."""

    def __init__(self, sep=":", linesep="\n"):
        ModelFile.__init__(self, sep, linesep)

        # General
        self.add_custom('fs_name', FSName())
        self.add_element('description',       check='string')

        # Stripping
        self.add_element('stripe_size',       check='digit', default=1048576)
        self.add_element('stripe_count',      check='digit', default=1)

        # Common target options
        for tgt in ['mgt', 'mdt', 'ost' ]:
            self.add_element(tgt + "_mkfs_options",  check='string')
            self.add_element(tgt + "_mount_options", check='string')
            self.add_element(tgt + "_format_params", check='string')
        self.add_element("mgt_mount_path",    check='string',
                default='/mnt/$fs_name/mgt')
        self.add_element("mdt_mount_path",    check='string',
                default='/mnt/$fs_name/mdt/$index')
        self.add_element("ost_mount_path",    check='string',
                default='/mnt/$fs_name/ost/$index')

        # Common client options
        self.add_element('mount_options',     check='string')
        self.add_element('mount_path',        check='path')

        # Quota
        self.add_element('quota',             check='boolean')
        self.add_element('quota_type',        check='string', default='ug')
        self.add_element('quota_bunit',       check='digit')
        self.add_element('quota_iunit',       check='digit')
        self.add_element('quota_btune',       check='digit')
        self.add_element('quota_itune',       check='digit')

        # NidMapping
        self.add_custom('nid_map', NidMaps())

        # Targets
        self.add_custom('mgt', Target(), multiple=True)
        self.add_custom('mdt', Target(), multiple=True)
        self.add_custom('ost', Target(), multiple=True)
        # Client
        self.add_custom('client', Client(), multiple=True)
        # Router
        self.add_custom('router', Router(), multiple=True)

        # Device action
        self.add_custom('dev_action', DeviceAction(), multiple=True,
                        expand_range=False)


class FSName(SimpleElement):
    """
    A 'string' SimpleElement which also check that value length is 8 or less.
    """

    def __init__(self, check='string', default=None, values=None):
        SimpleElement.__init__(self, check, default, values)

    def _validate(self, value):
        """Call SimpleElement validate method and also check value length."""
        value = SimpleElement._validate(self, value)
        if len(value) > 8:
            raise ModelFileValueError(
                           "Name '%s' should be 8-character long max" % value)
        return value


class NidMap(ModelFile):
    """Define 'nid_map' in model file: nodes=<NODES> nids=<NODES>@<NETWORK>"""

    def __init__(self, sep='=', linesep=' '):
        ModelFile.__init__(self, sep, linesep)
        self.add_element('nodes', check='string')
        self.add_element('nids',  check='string')


class NidMaps(MultipleElement):
    """Group all 'nid_map' declarations."""

    def __init__(self, orig_elem=None):
        MultipleElement.__init__(self, NidMap())

    def _expand_range(self, data):
        """
        This function is a no-op for NidMaps.

        NidMaps declaration should not be expanded like target.
        """
        return iter([data])


class Target(ModelFile):
    """Define 'mgt', 'mdt', 'ost' in model file."""

    def __init__(self, sep='=', linesep=' '):
        ModelFile.__init__(self, sep, linesep)
        self.add_element('node',    check='string')
        self.add_element('ha_node', check='string', multiple=True)
        self.add_element('dev',     check='path')
        self.add_element('jdev',    check='path')
        self.add_element('index',   check='digit')
        self.add_element('group',   check='string')
        self.add_element('mode',    check='enum',
                default='managed', values=['managed', 'external'])
        self.add_element('network', check='string')
        self.add_element('tag',     check='string')
        self.add_element('active',  check='enum',
                default='yes', values=['yes', 'no', 'nocreate', 'manual'])
        self.add_element('dev_run', check='string')

    def key(self):
        """
        A unique Target is identified by its index or, if missing, node and
        device path.
        """
        return self.get('index', (self.get('node'), self.get('dev')))

    def match_device(self, candidates):
        """
        Filter the `candidates` list with only those who shared the same key,
        value pairs.
        """
        matching = []

        # For each possible targets
        for target in candidates:

            # Verify my keys match its attributes
            for key, regexp in self.as_dict().iteritems():
                # Index and active have a special meaning
                # and should not be considered
                if key in ('index', 'active'):
                    continue
                # Key is missing, this does not match
                if key not in target:
                    break

                try:
                    # If this is a list
                    if type(regexp) is list:
                        bknds = target.get(key)
                        # If there's more criteria in model, it does not match
                        if len(regexp) > len(bknds):
                            break
                        # Match each criteria with its equivalent in backend
                        # definition. Break at first that differs.
                        if [ True for bk, rgexp in zip(bknds, regexp)
                                      if not re.match('^' + rgexp + '$', bk) ]:
                            break

                    # Or a simple element
                    elif not re.match('^' + regexp + '$', target.get(key)):
                        break

                except re.error:
                    raise ModelFileValueError("Bad syntax: %s" % regexp)

            # Ok, everything matches, add it
            else:
                matching.append(target)

        return matching

class Router(ModelFile):
    """Define 'router' in model file: nodes=<NODES>"""

    def __init__(self, sep='=', linesep=' '):
        ModelFile.__init__(self, sep, linesep)
        self.add_element('node',    check='string')


class Client(ModelFile):
    """
    Define 'client' in model file:
    nodes=<NODES> [mount_path=<PATH>] [mount_options=<PATH>]
    """

    def __init__(self, sep='=', linesep=' '):
        ModelFile.__init__(self, sep, linesep)
        self.add_element('node',          check='string')
        self.add_element('mount_options', check='string')
        self.add_element('mount_path',    check='path')

    def key(self):
        """A unique client is identified by its node and mount path."""
        return (self.get('node'), self.get('mount_path'))


class DeviceAction(ModelFile):
    """
    Define 'dev_action' in model file:
    alias=<ACTION_ALIAS> start=<COMMAND> stop=<COMMAND>
    """

    def __init__(self, sep='=', linesep=' '):
        ModelFile.__init__(self, sep, linesep)
        self.add_element('alias', check='string')
        self.add_element('start', check='string')
        self.add_element('stop', check='string')
