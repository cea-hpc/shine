# Install.py -- Install Lustre FS configuration
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

import os.path

from ClusterShell.NodeSet import NodeSet

from Shine.Lustre.Actions.Action import Action, CommonAction, ACT_OK, ACT_ERROR

class Install(CommonAction):
    """
    Action class: install file configuration requirements on remote nodes.
    """

    NAME = 'install'

    def __init__(self, nodes, fs, config_file, comps=None, **kwargs):
        CommonAction.__init__(self)
        self.nodes = nodes
        self.fs = fs
        self.config_file = config_file
        self._comps = comps
        self.dryrun = kwargs.get('dryrun', False)

    def _launch(self):
        """Copy local configuration file to remote nodes."""
        msg = '[COPY] %s on %s' % (self.config_file, self.nodes)
        self.fs.hdlr.log('detail', msg=msg)
        if self.dryrun:
            self.set_status(ACT_OK)
        else:
            self.task.copy(self.config_file, self.config_file,
                           nodes=self.nodes, handler=self)

    def ev_start(self, worker):
        CommonAction.ev_start(self, worker)
        name = os.path.basename(self.config_file)
        if len(self.nodes) > 8:
            msg = "Updating configuration file `%s' on %d servers" % \
                                                        (name, len(self.nodes))
        else:
            msg = "Updating configuration file `%s' on %s" % (name, self.nodes)
        self.fs.hdlr.log('verbose', msg)

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        Action.ev_close(self, worker)

        # Action timed out
        if worker.did_timeout():
            nodes = NodeSet.fromlist(worker.iter_keys_timeout())
            self.fs._handle_shine_proxy_error(nodes, "Nodes timed out")
            self.set_status(ACT_ERROR)

        # Action succeeded
        elif max(rc for rc, _ in worker.iter_retcodes()) == 0:
            self.set_status(ACT_OK)

        # Action failed
        else:
            for rc, nodes in worker.iter_retcodes():
                if rc == 0:
                    continue

                # Avoid warnings, flag this component in error state
                for comp in self._comps or []:
                    comp.sanitize_state(nodes=worker.nodes)

                for output, nodes in worker.iter_buffers(match_keys=nodes):
                    nodes = NodeSet.fromlist(nodes)
                    msg = "Copy failed: %s" % output
                    self.fs._handle_shine_proxy_error(nodes, msg)
            self.set_status(ACT_ERROR)
