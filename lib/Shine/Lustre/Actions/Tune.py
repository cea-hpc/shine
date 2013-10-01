# Tune.py -- Tune Lustre /proc files.
# Copyright (C) 2013 CEA
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
Classes used the apply tuning on local node, either from tuning.conf or
dynamically created.
"""

from Shine.Lustre.Actions.Action import CommonAction, ActionGroup

_SRVTYPE_MAP = {
        'mgt': 'mgs',
        'mdt': 'mds',
        'ost': 'oss',
        'client': 'client',
        'router': 'router'
    }

class _TuningAction(CommonAction):
    """Action handling the command to modify only 1 tuning."""

    NAME = "tuning"

    def __init__(self, command):
        CommonAction.__init__(self)
        self._command = command

    def _launch(self):
        self.task.shell(self._command, handler=self)


class Tune(ActionGroup):
    """Action to apply all tunings for the local node."""

    NAME = "tune"

    def __init__(self, srv, tuning_conf, comps, fsname):
        ActionGroup.__init__(self)
        self._server = srv
        self._comps = comps
        self._conf = tuning_conf
        self._fsname = fsname
        self._init = False

    def _add_actions(self):
        """
        Create all individual tunings Action.

        To be run before this fake group action is really launched.
        """
        srvtypes = set([_SRVTYPE_MAP.get(comp.TYPE) for comp in self._comps])
        srvname = str(self._server.hostname)

        tunings = self._conf.get_params_for_name(srvname, srvtypes)
        for tuning in tunings:
            cmds = tuning.build_tuning_command(self._fsname)
            for command in cmds:
                self.add(_TuningAction(command))

        # Actions has been added, no need to create them again.
        self._init = True

    def launch(self):
        # First time launch is called, we need to create all the sub actions.
        # As the graph is calling launch a couple of times, we need to do this
        # only once.
        if not self._init:
            self._add_actions()
        # Then call the real launch().
        ActionGroup.launch(self)
