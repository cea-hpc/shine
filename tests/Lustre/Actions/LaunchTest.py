# test suite for launch() method in Shine.Lustre.Actions.*
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

import types
import unittest
import Utils

from Shine.Lustre.Actions.Action import ACT_OK, ACT_ERROR
from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.Server import Server
from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Component import MOUNTED, OFFLINE, TARGET_ERROR, RUNTIME_ERROR

from Shine.Lustre.Actions.Proxy import shine_msg_pack


class ActionsTest(unittest.TestCase):

    class ActionEH(EventHandler):
        def __init__(self):
            EventHandler.__init__(self)
            self.evlist = dict()
        def event_callback(self, compname, action, status, **kwargs):
            self.evlist['%s_%s_%s' % (compname, action, status)] = kwargs
        def clear(self):
            self.evlist.clear()
        def result(self, compname, action, status):
            evname = '%s_%s_%s' % (compname, action, status)
            return self.evlist[evname]['result']

    def assert_events(self, compname, action, status_list):
        self.assertEqual(len(self.eh.evlist), len(status_list))
        for status in status_list:
            evname = '%s_%s_%s' % (compname, action, status)
            evlist = ', '.join(self.eh.evlist)
            self.assertTrue(evname in self.eh.evlist,
                            "'%s' not in event list: %s" % (evname, evlist))

    def format(self):
        self.tgt.format().launch()
        self.fs._run_actions()
        self.eh.clear()

    def setUp(self):
        self.eh = self.ActionEH()
        self.fs = FileSystem('action', event_handler=self.eh)
        srv1 = Server("localhost", ["localhost@tcp"])
        self.disk = Utils.make_disk()
        self.tgt = self.fs.new_target(srv1, 'mgt', 0, self.disk.name)

    def tearDown(self):
        self.tgt.lustre_check()
        if self.tgt.is_started():
            self.tgt.stop().launch()
            self.fs._run_actions()

    #
    # Format
    #

    @Utils.rootonly
    def test_format_ok(self):
        """Format a simple MGT"""
        act = self.tgt.format()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'format', ['start', 'done'])
        result = self.eh.result('mgt', 'format', 'done')
        self.assertEqual(result.retcode, 0)

        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_format_if_started(self):
        """Format when target is started failed"""
        def check_set_online(self):
            self.__class__.lustre_check(self)
            self.state = MOUNTED
        self.tgt.lustre_check = types.MethodType(check_set_online, self.tgt)

        act = self.tgt.format()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'format', ['start', 'failed'])
        result = self.eh.result('mgt', 'format', 'failed')
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.tgt.state, TARGET_ERROR)
        self.assertEqual(act.status(), ACT_ERROR)

    @Utils.rootonly
    def test_format_with_error(self):
        """Format with bad options is an error"""
        act = self.tgt.format(addopts="--BAD-OPTIONS")
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'format', ['start', 'failed'])
        result = self.eh.result('mgt', 'format', 'failed')
        self.assertEqual(result.retcode, 22)

        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_ERROR)

    # XXX: Add tests with Journal

    #
    # Fsck
    #
    @Utils.rootonly
    def test_fsck_ok(self):
        """Fsck on a freshly formatted target is ok"""
        self.format()
        act = self.tgt.fsck()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'fsck', ['start', 'progress', 'done'])
        result = self.eh.result('mgt', 'fsck', 'done')
        self.assertEqual(result.retcode, 0)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_fsck_repairs(self):
        """Fsck repairs a corruption"""
        self.format()
        # Corrupt FS
        self.disk.seek(1024)
        self.disk.write('\0' * 1024)
        self.disk.flush()
        act = self.tgt.fsck()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'fsck', ['start', 'progress', 'done'])
        result = self.eh.result('mgt', 'fsck', 'done')
        self.assertEqual(result.message, "Errors corrected")
        self.assertEqual(result.retcode, 1)

        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_fsck_no_repair(self):
        """Fsck detects but does not repair a corruption with -n"""
        self.format()
        # Corrupt FS
        self.disk.seek(1024)
        self.disk.write('\0' * 1024)
        self.disk.flush()
        act = self.tgt.fsck(addopts='-n')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'fsck', ['start', 'progress', 'done'])
        result = self.eh.result('mgt', 'fsck', 'done')
        self.assertEqual(result.message, "Errors found but NOT corrected")
        self.assertEqual(result.retcode, 4)

        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_fsck_with_error(self):
        """Fsck on an unformated device fails"""
        act = self.tgt.fsck()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'fsck', ['start', 'failed'])
        result = self.eh.result('mgt', 'fsck', 'failed')
        self.assertEqual(result.retcode, 8)

        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_ERROR)

    #
    # Execute
    #
    def test_execute_ok(self):
        """Execute of a simple command is ok"""
        act = self.tgt.execute(addopts='/bin/echo %device', mountdata='never')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'execute', ['start', 'done'])
        result = self.eh.result('mgt', 'execute', 'done')
        self.assertEqual(result.retcode, 0)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    def test_execute_error(self):
        """Execute a bad command fails"""
        act = self.tgt.execute(addopts='/bin/false', mountdata='never')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'execute', ['start', 'failed'])
        result = self.eh.result('mgt', 'execute', 'failed')
        self.assertEqual(result.retcode, 1)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_ERROR)

    @Utils.rootonly
    def test_execute_check_mountdata(self):
        """Execute a command with mountdata check"""
        self.format()
        act = self.tgt.execute(addopts="ls %device", mountdata='always')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'execute', ['start', 'done'])
        result = self.eh.result('mgt', 'execute', 'done')
        self.assertEqual(result.retcode, 0)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)

    #
    # Status
    #
    @Utils.rootonly
    def test_status_ok(self):
        """Status on a simple target"""
        self.format()
        act = self.tgt.status()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'status', ['start', 'done'])
        result = self.eh.result('mgt', 'status', 'done')
        self.assertEqual(result, None)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    def test_status_error(self):
        """Status on a not-formated target fails"""
        act = self.tgt.status()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'status', ['start', 'failed'])
        result = self.eh.result('mgt', 'status', 'failed')
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.tgt.state, TARGET_ERROR)
        # XXX: Should we set an error even if job was done correctly?
        self.assertEqual(act.status(), ACT_ERROR)

    #
    # Start Target
    #
    @Utils.rootonly
    def test_start_ok(self):
        """Start a simple target"""
        self.format()
        act = self.tgt.start()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'start', ['start', 'done'])
        result = self.eh.result('mgt', 'start', 'done')
        self.assertEqual(result.retcode, 0)
        # Status checks
        self.assertEqual(self.tgt.state, MOUNTED)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_start_already_done(self):
        """Start an already mounted target returns ok"""
        self.format()
        def is_started(self):
            self.state = MOUNTED
            return True
        self.tgt.is_started = types.MethodType(is_started, self.tgt)
        act = self.tgt.start()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'start', ['start', 'done'])
        result = self.eh.result('mgt', 'start', 'done')
        self.assertEqual(result.message, "MGS is already started")
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.tgt.state, MOUNTED)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_start_error(self):
        """Start an non-formated target fails"""
        act = self.tgt.start()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'start', ['start', 'failed'])
        result = self.eh.result('mgt', 'start', 'failed')
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.tgt.state, TARGET_ERROR)
        self.assertEqual(act.status(), ACT_ERROR)

    #
    # Stop Target
    #
    @Utils.rootonly
    def test_stop_ok(self):
        """Start a simple target"""
        self.format()
        # Start the target, to be able to unmount it after
        act = self.tgt.start()
        act.launch()
        self.fs._run_actions()
        self.eh.clear()

        act = self.tgt.stop()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'stop', ['start', 'done'])
        result = self.eh.result('mgt', 'stop', 'done')
        self.assertEqual(result.retcode, 0)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_stop_already_done(self):
        """Stop an already stopped target fails"""
        self.format()
        act = self.tgt.stop()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'stop', ['start', 'done'])
        result = self.eh.result('mgt', 'stop', 'done')
        self.assertEqual(result.message, "MGS is already stopped")
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_stop_error(self):
        """Stop target failure is an error"""
        self.format()
        # Start the target, to be able to unmount it after
        self.tgt.start().launch()
        self.fs._run_actions()
        self.eh.clear()

        act = self.tgt.stop()
        def _prepare_cmd(_self):
            return [ "/bin/false" ]
        act._prepare_cmd = types.MethodType(_prepare_cmd, act)
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('mgt', 'stop', ['start', 'failed'])
        result = self.eh.result('mgt', 'stop', 'failed')
        self.assertEqual(result.retcode, 1)
        # Status checks
        self.assertEqual(self.tgt.state, MOUNTED)
        self.assertEqual(act.status(), ACT_ERROR)

    #
    # Server test (special)
    # This test needs a running MGS, it is better to put it here.
    #

    @Utils.rootonly
    def test_module_busy(self):
        """Unloading module with a started MGS is an error"""
        self.format()
        # Start the target, to set module busy
        self.tgt.start().launch()
        self.fs._run_actions()

        srv = self.tgt.server
        act = srv.unload_modules()
        act.launch()
        self.fs._run_actions()

        # Status check
        self.assertEqual(sorted(srv.modules.keys()), ['ldiskfs', 'libcfs'])
        self.assertEqual(act.status(), ACT_ERROR)


class ServerActionTest(unittest.TestCase):

    def _clean_modules(self):
        """Remove all already loaded modules, before a test."""
        self.srv.lustre_check()
        if 'libcfs' in self.srv.modules or 'ldiskfs' in self.srv.modules:
            self.srv.unload_modules().launch()
            self.fs._run_actions()

    def setUp(self):
        self.srv = Server('localhost', ['127.0.0.1@lo'])
        self.fs = FileSystem('srvaction')
        self._clean_modules()

    def tearDown(self):
        self._clean_modules()

    #
    # Modules
    #

    @Utils.rootonly
    def test_module_load(self):
        """Load lustre modules is ok"""
        act = self.srv.load_modules()
        act.launch()
        self.fs._run_actions()

        # Status check
        self.assertEqual(sorted(self.srv.modules.keys()), ['libcfs', 'lustre'])
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_module_load_custom(self):
        """Load a custom module is ok"""
        act = self.srv.load_modules(modname='ldiskfs')
        act.launch()
        self.fs._run_actions()

        # Status check
        self.assertEqual(self.srv.modules.keys(), ['ldiskfs'])
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_module_load_error(self):
        """Load a bad module is an error"""
        act = self.srv.load_modules(modname='ERROR')
        act.launch()
        self.fs._run_actions()

        # Status check
        self.assertEqual(self.srv.modules, {})
        self.assertEqual(act.status(), ACT_ERROR)

    @Utils.rootonly
    def test_module_load_already_done(self):
        """Load modules when already loaded is ok"""
        def lustre_check(self):
            self.modules = {'lustre': 0, 'libcfs': 1}
        self.srv.lustre_check = types.MethodType(lustre_check, self.srv)
        act = self.srv.load_modules()
        act.launch()
        self.fs._run_actions()

        # Status check
        self.assertEqual(sorted(self.srv.modules.keys()), ['libcfs', 'lustre'])
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_module_unload(self):
        """Unload modules"""
        # First load modules
        self.srv.load_modules().launch()
        self.fs._run_actions()

        act = self.srv.unload_modules()
        act.launch()
        self.fs._run_actions()

        # Status check
        self.assertEqual(self.srv.modules, {})
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_module_unload_already_done(self):
        """Unload modules when already done is ok"""
        # By default modules are not loaded
        act = self.srv.unload_modules()
        act.launch()
        self.fs._run_actions()

        # Status check
        self.assertEqual(self.srv.modules, {})
        self.assertEqual(act.status(), ACT_OK)


class ProxyTest(unittest.TestCase):

    def setUp(self):
        self.fs = FileSystem('proxy')
        self.srv1 = Server(Utils.HOSTNAME, ["%s@tcp" % Utils.HOSTNAME])
        disk = Utils.makeTempFilename()
        self.tgt = self.fs.new_target(self.srv1, 'mgt', 0, disk)

        self.act = self.fs._proxy_action('start', self.srv1.hostname,
                                         self.fs.components)
        def fakeprepare(action):
            return [action.fakecmd]
        self.act._prepare_cmd = types.MethodType(fakeprepare, self.act)

    def test_exec_fail(self):
        """simulate unable to run python"""
        self.act.fakecmd = '/bin/false'
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([MOUNTED], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 1)
        self.assertEqual(self.fs.proxy_errors[0][1],
                         "Remote action start failed: No response")
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)
        self.assertEqual(self.act.status(), ACT_ERROR)

    def test_start_crash(self):
        """send a start message then crashes"""
        msg = shine_msg_pack(compname=self.tgt.TYPE, action='start',
                             status='start', comp=self.tgt)

        self.act.fakecmd = 'echo "%s"; echo BAD; exit 1' % msg
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([MOUNTED], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 1)
        self.assertEqual(self.fs.proxy_errors[0][1],
                         "Remote action start failed: \nBAD\n")
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)
        self.assertEqual(self.act.status(), ACT_ERROR)

    def test_start_ok(self):
        """send a start and done message"""
        msgs = []
        msgs.append(shine_msg_pack(compname=self.tgt.TYPE, action='start',
                                   status='start', comp=self.tgt))
        self.tgt.state = MOUNTED
        msgs.append(shine_msg_pack(compname=self.tgt.TYPE, action='start',
                                   status='done', comp=self.tgt))

        self.act.fakecmd = 'echo "%s"' % '\n'.join(msgs)
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([MOUNTED], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 0)
        self.assertEqual(self.tgt.state, MOUNTED)
        self.assertEqual(self.act.status(), ACT_OK)

    def test_crash_after_start_ok(self):
        """send a start and done message and then crashes"""
        msgs = []
        msgs.append(shine_msg_pack(compname=self.tgt.TYPE, action='start',
                                   status='start', comp=self.tgt))
        self.tgt.state = MOUNTED
        msgs.append(shine_msg_pack(compname=self.tgt.TYPE, action='start',
                                   status='done', comp=self.tgt))

        self.act.fakecmd = 'echo "%s"; echo Oops; exit 1' % '\n'.join(msgs)
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([MOUNTED], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 1)
        self.assertEqual(self.fs.proxy_errors[0][1],
                         "Remote action start failed: \n\nOops\n")
        self.assertEqual(self.tgt.state, MOUNTED)
        self.assertEqual(self.act.status(), ACT_ERROR)
