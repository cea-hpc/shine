# Tune.py -- Tune Lustre /proc files.
# Copyright (C) 2013-2015 CEA
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

from Shine.Lustre.Actions.Action import CommonAction, ActionGroup, \
                                        ActionInfo, \
                                        ACT_OK, ACT_ERROR, ErrorResult

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

    def __init__(self, action, command):
        CommonAction.__init__(self)
        self._tune = action
        self._command = command
        self.dryrun = action.dryrun

    def _launch(self):
        self._tune._server.hdlr.log('detail',
                                    msg='[RUN] %s' % self._command)
        if self.dryrun:
            self.task.shell(':', handler=self)
        else:
            self.task.shell(self._command, handler=self)


class Tune(ActionGroup):
    """Action to apply all tunings for the local node."""

    NAME = "tune"

    def __init__(self, srv, tuning_conf, comps, fsname, **kwargs):
        ActionGroup.__init__(self)
        self._server = srv
        self._comps = comps
        self._conf = tuning_conf
        self._fsname = fsname
        self._init = False
        self.dryrun = kwargs.get('dryrun', False)

    def info(self):
        """Return a ActionInfo describing this action."""
        return ActionInfo(self, self._server, 'apply tunings')

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
                self.add(_TuningAction(self, command))

    def set_status(self, status):
        """
        Update action status.

        If this is a final state, raise corresponding events.
        """
        # Do not raise events if start event was not raised.
        # Start event is raised when init is set.
        if self._init:
            if status == ACT_OK:
                self._server.action_event(self, 'done')
            elif status == ACT_ERROR:
                # Build an error string
                errors = []
                for act in self:
                    if act.status() == ACT_ERROR:
                        errors.append("'%s' failed" % act._command)
                result = ErrorResult("\n".join(errors))
                self._server.action_event(self, 'failed', result)

        ActionGroup.set_status(self, status)

    def _launch(self):
        # First time launch is called, we need to create all the sub actions.
        # As the graph is calling launch a couple of times, we need to do this
        # only once.
        if not self._init:
            self._server.action_event(self, 'start')
            self._add_actions()
            self._init = True
        # Then call the real _launch()
        ActionGroup._launch(self)
