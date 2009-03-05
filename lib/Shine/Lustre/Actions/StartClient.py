# StartClient.py -- Mount client
# Copyright (C) 2009 CEA
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

import re

from Action import Action

class StartClient(Action):
    """
    File system client start (ie. mount) action class.
    """

    def __init__(self, client, **kwargs):
        Action.__init__(self)
        self.client = client
        assert self.client != None
        self.mount_options = kwargs.get('mount_options')
        self.abort_recovery = kwargs.get('abort_recovery')

    def launch(self):
        """
        Mount file system client.
        """
        command = ["mkdir", "-p", "\"%s\"" % self.client.mount_path]
        command += ["&&", "mount", "-t", "lustre"]

        # Other custom mount options
        if self.mount_options:
            command.append("-o")
            command.append(self.mount_options)

        # MGS NIDs

        command.append("%s:/%s" % (':'.join(self.client.fs.get_mgs_nids()),
            self.client.fs.fs_name))

        command.append(self.client.mount_path)

        self.task.shell(' '.join(command), handler=self) ### timeout

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        if worker.retcode() == 0:
            self.client.fs._invoke('ev_startclient_done', client=self.client)
        else:
            self.client.fs._invoke('ev_startclient_failed', client=self.client,
                    rc=worker.retcode(), message=worker.read())

