# StartClient.py -- Umount client
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


from Action import Action

class StopClient(Action):
    """
    File system client stop (ie. umount) action class.
    """

    def __init__(self, client, **kwargs):
        Action.__init__(self)
        self.client = client
        assert self.client != None
        self.failout = kwargs.get('failout')

    def launch(self):
        """
        Unmount file system client.
        """
        command = ["umount"]

        # Failout option
        if self.failout:
            command.append("-f")

        command.append(self.client.mount_path)

        self.task.shell(' '.join(command), handler=self) ### timeout

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.
        """
        if worker.retcode() == 0:
            self.client.fs._invoke('ev_stopclient_done', client=self.client)
        else:
            self.client.fs._invoke('ev_stopclient_failed', client=self.client,
                    rc=worker.retcode(), message=worker.read())

