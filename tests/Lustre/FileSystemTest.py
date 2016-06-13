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
from Shine.Lustre.FileSystem import FileSystem, Server, FSRemoteError, \
                                    MOUNTED, OFFLINE, MIGRATED


def _graph2obj(graph):
    try:
        return [_graph2obj(item) for item in graph]
    except TypeError:
        result = {}
        for key in ('NAME', 'comp', 'action', 'config_file'):
            if hasattr(graph, key):
                result[key] = getattr(graph, key)
        return result

class FakeTunings(object):
    def __init__(self, filename='foo'):
        self.filename = filename


class PrepareTest(unittest.TestCase):
    """Verify graph from _prepare()"""

    def setUp(self):
        self.fs = FileSystem('prepare')
        self.remotesrv = Server('remote', ['remote@tcp'])
        self.localsrv = Server(Utils.HOSTNAME, ['%s@tcp' % Utils.HOSTNAME])
        self.fs.local_server = self.localsrv

    def test_simple_local_action(self):
        """prepare a simple action on a local component"""
        comp = self.fs.new_target(self.localsrv, 'mgt', 0, '/dev/fakedev')
        graph = self.fs._prepare('start')

        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'start', 'comp': comp}],
                           [{'NAME': 'load modules'},
                            {'NAME': 'load modules'}]]])
        self.assertEqual(graph[0][1][0]._modname, 'lustre')

    def test_simple_remote_action(self):
        """prepare a simple action on a remote component"""
        self.fs.new_target(self.remotesrv, 'mgt', 0, '/dev/fakedev')
        graph = self.fs._prepare('start')

        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'proxy', 'action': 'start'}]]])
        self.assertEqual(str(graph[0][0][0].nodes), 'remote')

    def test_proxy_tunings(self):
        """prepare is ok with or without tunings"""
        self.fs.new_target(self.remotesrv, 'mgt', 0, '/dev/fakedev')

        # Without tunings
        graph = self.fs._prepare('dummy', tunings=None)
        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'proxy', 'action': 'dummy'}]]])
        self.assertEqual(str(graph[0][0][0].nodes), 'remote')

        # With tunings
        graph = self.fs._prepare('dummy', tunings=FakeTunings())
        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'install', 'config_file': 'foo'},
                            {'NAME': 'proxy', 'action': 'dummy'}]]])
        self.assertEqual(str(graph[0][0][1].nodes), 'remote')

        # With tunings but without tuning_file
        graph = self.fs._prepare('dummy', tunings=FakeTunings(None))
        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'proxy', 'action': 'dummy'}]]])
        self.assertEqual(str(graph[0][0][0].nodes), 'remote')

    def test_local_tunings(self):
        """prepare is ok with or without tunings"""
        comp = self.fs.new_target(self.localsrv, 'mgt', 0, '/dev/fakedev')

        # Without tunings
        graph = self.fs._prepare('start', tunings=None)
        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'start', 'comp': comp}],
                           [{'NAME': 'load modules'},
                            {'NAME': 'load modules'}]]])
        self.assertEqual(graph[0][1][0]._modname, 'lustre')

        # With tunings
        graph = self.fs._prepare('start', tunings=FakeTunings())
        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'start', 'comp': comp}],
                           [{'NAME': 'load modules'},
                            {'NAME': 'load modules'}], []]])
        self.assertEqual(graph[0][1][0]._modname, 'lustre')
        self.assertEqual(graph[0][2].NAME, 'tune')

    def test_need_unload(self):
        """prepare handles need_unload correctly"""
        comp = self.fs.new_target(self.localsrv, 'mgt', 0, '/dev/fakedev')

        # Without module unload
        graph = self.fs._prepare('stop', need_unload=False)
        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'stop', 'comp': comp}]]])

        # With module unload
        graph = self.fs._prepare('stop', need_unload=True)
        self.assertEqual(_graph2obj(graph),
                         [[[{'NAME': 'stop', 'comp': comp}],
                           {'NAME': 'unload modules'}]])


class SimpleFileSystemTest(unittest.TestCase):
    """Tests which do not setup a real Lustre filesystem."""

    def test_install_nothing(self):
        """install only using local node does nothing"""
        class MyFS(FileSystem):
            def _run_actions(obj):
                self.fail("should not be called")
        fs = MyFS('testfs')
        srv = Server(Utils.HOSTNAME, ['%s@tcp' % Utils.HOSTNAME])
        fs.local_server = srv
        fs.new_target(srv, 'mgt', 0, '/dev/fakedev')
        fs.install(fs_config_file=Utils.makeTempFilename())

    def test_install_unreachable(self):
        """install on unreachable nodes raises an error"""
        fs = FileSystem('testfs')
        badsrv1 = Server('badnode1', ['127.0.0.2@tcp'])
        badsrv2 = Server('badnode2', ['127.0.0.3@tcp'])
        fs.new_target(badsrv1, 'mgt', 0, '/dev/fakedev')
        fs.new_client(badsrv2, '/testfs')
        try:
            fs.install(fs_config_file=Utils.makeTempFilename())
        except FSRemoteError, ex:
            self.assertEqual(str(ex.nodes), 'badnode[1-2]')
            self.assertEqual(ex.rc, 1)
            # Partial comparison to support RHEL5 OpenSSH output
            self.assertTrue(str(ex).startswith("badnode[1-2]: Copy failed: "))
            self.assertTrue(str(ex).endswith("badnode[1-2]: Name or service not"
                                             " known\nlost connection [rc=1]"))
        else:
            self.fail("did not raise FSRemoteError")


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
        self.assertEqual(self.fs.format(), set([OFFLINE]))

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
        self.assertEqual(self.fs.start(), set([MIGRATED]))
        self.assertEqual(mgt.state, MOUNTED)
        self.assertEqual(mdt.state, MIGRATED)
