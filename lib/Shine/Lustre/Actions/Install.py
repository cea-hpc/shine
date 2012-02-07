# Install.py -- Install Lustre FS configuration
# Copyright (C) 2007-2011 CEA
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

import os.path

from Shine.Lustre.Actions.Action import Action

class Install(Action):
    """
    Action class: install file configuration requirements on remote nodes.
    """

    def __init__(self, nodes, fs, config_file):
        Action.__init__(self)
        self.nodes = nodes
        self.fs = fs
        self.config_file = config_file

    def launch(self):
        """
        Copy local configuration file to remote nodes.
        """
        self.task.copy(self.config_file, self.config_file,
                nodes=self.nodes, handler=self)

    def ev_start(self, worker):
        Action.ev_start(self, worker)
        name = os.path.basename(self.config_file)
        if len(self.nodes) > 8:
            print "Updating file system configuration file `%s' on %d " \
                "server(s)" % (name, len(self.nodes))
        else:
            print "Updating file system configuration file `%s' on %s" \
                % (name, self.nodes)
