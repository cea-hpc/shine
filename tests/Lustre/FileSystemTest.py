#
# Copyright (C) 2017 CEA
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


import unittest
import Utils

from Shine.Lustre.Server import ServerGroup
from Shine.Lustre.FileSystem import FileSystem, Server, \
                                    MOUNTED, OFFLINE, MIGRATED

class FileSystemTest(unittest.TestCase):

    def setUp(self):
        self.srv1 = Server(Utils.HOSTNAME, ['%s@tcp' % Utils.HOSTNAME])

        self.disk1 = Utils.make_disk()
        self.disk2 = Utils.make_disk()

        self.fs = FileSystem('testfs')
        self.fs.local_server = self.srv1

    def tearDown(self):
        self.fs.stop()

    @Utils.rootonly
    def test_start_failover(self):
        """start on a failover node"""
        srv2 = Server('fakenode', ['127.0.0.2@tcp'])

        mgt = self.fs.new_target(self.srv1, 'mgt', 0, self.disk1.name)
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, self.disk2.name)
        mdt.add_server(srv2)
        self.assertEqual(self.fs.format(), OFFLINE)

        # For a simpler test environment, simulate local node is the failover
        # node.
        # This could be improved when --servicenode will be supported. Format
        # will be possible directly in failover configuration (no need to
        # reconfig anymore).
        mdt.state = None
        mdt.defaultserver = srv2
        mdt.failservers = ServerGroup()
        mdt.add_server(self.srv1)

        # Fail over this local node (-F HOSTNAME -n HOSTNAME)
        mdt.failover(self.srv1.hostname)
        srv2.action_enabled = False

        # Start should succeed and detect migration
        self.assertEqual(self.fs.start(), MIGRATED)
        self.assertEqual(mgt.state, MOUNTED)
        self.assertEqual(mdt.state, MIGRATED)
