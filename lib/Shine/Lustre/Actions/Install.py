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

from Shine.Lustre.Actions.Action import Action, CommonAction, ACT_OK, ACT_ERROR

class Install(CommonAction):
    """
    Action class: install file configuration requirements on remote nodes.
    """

    def __init__(self, nodes, fs, config_file, **kwargs):
        CommonAction.__init__(self)
        self.nodes = nodes
        self.fs = fs
        self.config_file = config_file
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
        self.fs.hdlr.log('info', msg)

    def ev_read(self, worker):
        """Log any configuration file copy messages."""
        self.fs.hdlr.log('info', "%s: %s" % (worker.current_node,
                                             worker.current_msg))

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        Action.ev_close(self, worker)

        # Action timed out
        if worker.did_timeout():
            self.set_status(ACT_ERROR)

        # Action succeeded
        elif max(rc for rc, _ in worker.iter_retcodes()) == 0:
            self.set_status(ACT_OK)

        # Action failed
        else:
            self.set_status(ACT_ERROR)
