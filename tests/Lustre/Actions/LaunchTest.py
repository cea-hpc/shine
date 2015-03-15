# test suite for launch() method in Shine.Lustre.Actions.*
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

import os
import copy
import types
import unittest
import Utils


from Shine.Configuration.TuningModel import TuningModel

from Shine.Lustre.Actions.Action import ACT_OK, ACT_ERROR
from Shine.Lustre.Actions.Install import Install
from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.Server import Server
from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Component import MOUNTED, OFFLINE, TARGET_ERROR


class CommonTestCase(unittest.TestCase):

    class ActionEH(EventHandler):
        def __init__(self):
            EventHandler.__init__(self)
            self.evlist = dict()
            self.msglist = []

        def event_callback(self, evtype, **kwargs):
            if 'info' in kwargs:
                status = kwargs.get('status')
                action = kwargs.get('info').actname
                self.evlist['%s_%s_%s' % (evtype, action, status)] = kwargs
            elif 'msg' in kwargs:
                self.msglist.append(kwargs['msg'])

        def clear(self):
            self.evlist.clear()
            self.msglist = []

        def result(self, evtype, action, status, key='result'):
            evname = '%s_%s_%s' % (evtype, action, status)
            return self.evlist[evname][key]

    def assert_events(self, evtype, action, status_list):
        evset = set(('%s_%s_%s' % (evtype, action, status)
                     for status in status_list))
        raisedset = set(self.eh.evlist.keys())
        self.assertEqual(evset, raisedset)

    def assert_info(self, evtype, action, status, elem, text):
        if not isinstance(status, list):
            status = [status]
        for sta in status:
            info = self.eh.result(evtype, action, sta, key='info')
            self.assertEqual(info.elem, elem)
            self.assertEqual(str(info), text)

    def check_dryrun(self, act, text, evtype, action, events, elem, desc):
        self.mock_shell(act)
        act.launch()
        self.fs._run_actions()

        # Callback checks
        text = '[RUN] ' + text
        self.assertEqual(self.eh.msglist, [text])
        self.assert_events(evtype, action, events)
        self.assertEqual(self.eh.result(evtype, action, events[-1]), None)
        self.assert_info(evtype, action, events, elem, desc)

        # Status checks
        self.assertEqual(act.status(), ACT_OK)

    def mock_shell(self, act):
        def shell(task, command, **kwargs):
            self.fail("dry-run should have prevent it")
        new_task = copy.copy(act.task)
        new_task.shell = types.MethodType(shell, new_task)
        act.task = new_task

    def mock_copy(self, act):
        def fake_copy(task, command, **kwargs):
            self.fail("dry-run should have prevent it")
        new_task = copy.copy(act.task)
        new_task.copy = types.MethodType(fake_copy, new_task)
        act.task = new_task

    def setUp(self):
        self.eh = self.ActionEH()
        self.fs = FileSystem('action', event_handler=self.eh)

class TargetActionTest(CommonTestCase):

    def format(self):
        self.tgt.format().launch()
        self.fs._run_actions()
        self.eh.clear()

    def setUp(self):
        self.eh = self.ActionEH()
        self.fs = FileSystem('action', event_handler=self.eh)
        srv1 = Server("localhost", ["localhost@tcp"], hdlr=self.eh)
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
        self.assert_events('comp', 'format', ['start', 'done'])
        result = self.eh.result('comp', 'format', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'format', 'start', self.tgt,
                         'format of MGS (%s)' % self.tgt.dev)
        self.assert_info('comp', 'format', 'done', self.tgt,
                         'format of MGS (%s)' % self.tgt.dev)

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
        self.assert_events('comp', 'format', ['start', 'failed'])
        result = self.eh.result('comp', 'format', 'failed')
        self.assertEqual(result.retcode, None)
        self.assert_info('comp', 'format', 'failed', self.tgt,
                         'format of MGS (%s)' % self.tgt.dev)

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
        self.assert_events('comp', 'format', ['start', 'failed'])
        result = self.eh.result('comp', 'format', 'failed')
        self.assertEqual(result.retcode, 22)

        # Hack for old mkfs.lustre with Lustre 1.8
        resultstr = str(result).replace("`--BAD-OPTIONS'", "'--BAD-OPTIONS'")
        self.assertEqual(resultstr,
                         "mkfs.lustre: unrecognized option '--BAD-OPTIONS'\n"
                         "mkfs.lustre: exiting with 22 (Invalid argument)")
        self.assert_info('comp', 'format', 'failed', self.tgt,
                         'format of MGS (%s)' % self.tgt.dev)

        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_ERROR)

    @Utils.rootonly
    def test_format_dryrun(self):
        """Format in dry-run mode"""
        act = self.tgt.format(dryrun=True)
        text = 'mkfs.lustre --reformat --quiet "--fsname=action"' \
               ' --mgs --device-size=204800 %s' % self.tgt.dev
        self.check_dryrun(act, text, 'comp', 'format', ['start', 'done'],
                          self.tgt, 'format of MGS (%s)' % self.tgt.dev)
        self.assertEqual(self.tgt.state, OFFLINE)


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
        self.assert_events('comp', 'fsck', ['start', 'progress', 'done'])
        result = self.eh.result('comp', 'fsck', 'done')
        self.assertEqual(result.retcode, 0)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_fsck_dryrun(self):
        """Fsck in dry-run mode"""
        self.format()
        act = self.tgt.fsck(dryrun=True)
        text = 'e2fsck -f -C2 %s -y' % self.tgt.dev
        self.check_dryrun(act, text, 'comp', 'fsck', ['start', 'done'],
                          self.tgt, 'fsck of MGS (%s)' % self.tgt.dev)
        self.assertEqual(self.tgt.state, OFFLINE)

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
        self.assert_events('comp', 'fsck', ['start', 'progress', 'done'])
        result = self.eh.result('comp', 'fsck', 'done')
        self.assertEqual(str(result), "Errors corrected")
        self.assertEqual(result.retcode, 1)
        self.assert_info('comp', 'fsck', 'done', self.tgt,
                         'fsck of MGS (%s)' % self.tgt.dev)

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
        self.assert_events('comp', 'fsck', ['start', 'progress', 'done'])
        result = self.eh.result('comp', 'fsck', 'done')
        self.assertEqual(str(result), "Errors found but NOT corrected")
        self.assertEqual(result.retcode, 4)
        self.assert_info('comp', 'fsck', 'done', self.tgt,
                         'fsck of MGS (%s)' % self.tgt.dev)

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
        self.assert_events('comp', 'fsck', ['start', 'failed'])
        result = self.eh.result('comp', 'fsck', 'failed')
        self.assertEqual(result.retcode, 8)
        self.assert_info('comp', 'fsck', 'start', self.tgt,
                         'fsck of MGS (%s)' % self.tgt.dev)

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
        self.assert_events('comp', 'execute', ['start', 'done'])
        result = self.eh.result('comp', 'execute', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'execute', 'done', self.tgt,
                         'execute of MGS (%s)' % self.tgt.dev)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    def test_execute_dryrun(self):
        """Execute of a command in dry-run mode"""
        act = self.tgt.execute(addopts='/bin/echo %device', mountdata='never',
                               dryrun=True)
        text = '/bin/echo %s' % self.tgt.dev
        self.check_dryrun(act, text, 'comp', 'execute', ['start', 'done'],
                          self.tgt, 'execute of MGS (%s)' % self.tgt.dev)
        self.assertEqual(self.tgt.state, OFFLINE)

    def test_execute_error(self):
        """Execute a bad command fails"""
        act = self.tgt.execute(addopts='/bin/false', mountdata='never')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'execute', ['start', 'failed'])
        result = self.eh.result('comp', 'execute', 'failed')
        self.assertEqual(result.retcode, 1)
        self.assert_info('comp', 'execute', 'failed', self.tgt,
                         'execute of MGS (%s)' % self.tgt.dev)
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
        self.assert_events('comp', 'execute', ['start', 'done'])
        result = self.eh.result('comp', 'execute', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'execute', 'start', self.tgt,
                         'execute of MGS (%s)' % self.tgt.dev)
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
        self.assert_events('comp', 'status', ['start', 'done'])
        result = self.eh.result('comp', 'status', 'done')
        self.assertEqual(result, None)
        self.assert_info('comp', 'status', 'start', self.tgt,
                         'status of MGS (%s)' % self.tgt.dev)
        # Status checks
        self.assertEqual(self.tgt.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    def test_status_error(self):
        """Status on a not-formated target fails"""
        act = self.tgt.status()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'status', ['start', 'failed'])
        result = self.eh.result('comp', 'status', 'failed')
        self.assertEqual(result.retcode, None)
        self.assert_info('comp', 'status', 'failed', self.tgt,
                         'status of MGS (%s)' % self.tgt.dev)
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
        self.assert_events('comp', 'start', ['start', 'done'])
        result = self.eh.result('comp', 'start', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'start', 'start', self.tgt,
                         'start of MGS (%s)' % self.tgt.dev)
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
        self.assert_events('comp', 'start', ['start', 'done'])
        result = self.eh.result('comp', 'start', 'done')
        self.assertEqual(str(result), "MGS is already started")
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
        self.assert_events('comp', 'start', ['start', 'failed'])
        result = self.eh.result('comp', 'start', 'failed')
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.tgt.state, TARGET_ERROR)
        self.assertEqual(act.status(), ACT_ERROR)

    #
    # Stop Target
    #
    @Utils.rootonly
    def test_stop_ok(self):
        """Stop a simple target"""
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
        self.assert_events('comp', 'stop', ['start', 'done'])
        result = self.eh.result('comp', 'stop', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'stop', 'start', self.tgt,
                         'stop of MGS (%s)' % self.tgt.dev)
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
        self.assert_events('comp', 'stop', ['start', 'done'])
        result = self.eh.result('comp', 'stop', 'done')
        self.assertEqual(str(result), "MGS is already stopped")
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
            return ["/bin/false"]
        act._prepare_cmd = types.MethodType(_prepare_cmd, act)
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'stop', ['start', 'failed'])
        result = self.eh.result('comp', 'stop', 'failed')
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
        """Unloading module with a started MGS is not considered as an error"""
        self.format()
        # Start the target, to set module busy
        self.tgt.start().launch()
        self.fs._run_actions()
        self.eh.clear()

        srv = self.tgt.server
        act = srv.unload_modules()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('server', 'unload modules', ['start', 'done'])
        result = self.eh.result('server', 'unload modules', 'done')
        # Hack for Lustre < 2.4
        resultstr = str(result).replace('2 in-use', '3 in-use')
        self.assertEqual(resultstr,
                         'ignoring, still 3 in-use lustre device(s)')
        self.assert_info('server', 'unload modules', 'start', srv,
                         'unload modules')

        # Status check
        self.assertTrue(set(['ldiskfs', 'libcfs', 'lustre']).issubset(
                        set(srv.modules.keys())))
        self.assertEqual(act.status(), ACT_OK)


class RouterActionTest(CommonTestCase):

    def net_up(self, options):
        self.srv1.load_modules(modname='lnet', options=options).launch()
        self.fs._run_actions()
        self.eh.clear()

    def setUp(self):
        self.eh = self.ActionEH()
        self.fs = FileSystem('action', event_handler=self.eh)
        self.srv1 = Server("localhost", ["localhost@tcp"])
        self.router = self.fs.new_router(self.srv1)
        self.srv1.unload_modules().launch()
        self.fs._run_actions()

    def tearDown(self):
        self.router.lustre_check()
        if self.router.is_started():
            self.router.stop().launch()
            self.fs._run_actions()
        self.srv1.unload_modules().launch()
        self.fs._run_actions()

    #
    # Start Router
    #
    @Utils.rootonly
    def test_start_router_ok(self):
        """Start a stopped router is ok"""
        self.net_up('forwarding=enabled')
        act = self.router.start()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'start', ['start', 'done'])
        result = self.eh.result('comp', 'start', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'start', 'start', self.router,
                         'start of router on %s' % self.router.server)
        # Status checks
        self.assertEqual(self.router.state, MOUNTED)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_start_router_dryrun(self):
        """Start a router in dry-run mode"""
        self.net_up('forwarding=enabled')
        act = self.router.start(dryrun=True)
        text = '/sbin/modprobe ptlrpc'
        self.check_dryrun(act, text, 'comp', 'start', ['start', 'done'],
                          self.router,
                          'start of router on %s' % self.router.server)
        self.assertEqual(self.router.state, OFFLINE)

    @Utils.rootonly
    def test_start_router_already_done(self):
        """Start an already started router is ok"""
        self.net_up('forwarding=enabled')
        # Start the router
        self.router.start().launch()
        self.fs._run_actions()
        self.eh.clear()

        # Then try to restart it
        act = self.router.start()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'start', ['start', 'done'])
        result = self.eh.result('comp', 'start', 'done')
        self.assertEqual(str(result), "router is already enabled")
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.router.state, MOUNTED)
        self.assertEqual(act.status(), ACT_OK)

    #
    # Stop Router
    #
    @Utils.rootonly
    def test_stop_router_ok(self):
        """Stop a started router is ok"""
        self.net_up('forwarding=enabled')
        # Start the router
        self.router.start().launch()
        self.fs._run_actions()
        self.eh.clear()

        # Then stop it
        act = self.router.stop()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'stop', ['start', 'done'])
        result = self.eh.result('comp', 'stop', 'done')
        self.assertEqual(result.retcode, 0)
        # Status checks
        self.assertEqual(self.router.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_stop_router_dryrun(self):
        """Stop a router in dryrun mode"""
        self.net_up('forwarding=enabled')
        # Start the router
        self.router.start().launch()
        self.fs._run_actions()
        self.eh.clear()

        # Then stop it
        act = self.router.stop(dryrun=True)
        text = 'lustre_rmmod'
        self.check_dryrun(act, text, 'comp', 'stop', ['start', 'done'],
                          self.router, 'stop of router on %s' %
                          self.router.server)
        self.assertEqual(self.router.state, MOUNTED)

    @Utils.rootonly
    def test_stop_router_already_done(self):
        """Stop an already stopped router fails"""
        self.net_up('forwarding=enabled')
        act = self.router.stop()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'stop', ['start', 'done'])
        result = self.eh.result('comp', 'stop', 'done')
        self.assertEqual(str(result), "router is already disabled")
        self.assertEqual(result.retcode, None)
        # Status checks
        self.assertEqual(self.router.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)


class ServerActionTest(CommonTestCase):

    def _clean_modules(self):
        """Remove all already loaded modules, before a test."""
        self.srv.lustre_check()
        if 'libcfs' in self.srv.modules or 'ldiskfs' in self.srv.modules:
            self.srv.unload_modules().launch()
            self.fs._run_actions()
            self.eh.clear()

    def setUp(self):
        self.eh = self.ActionEH()
        self.srv = Server('localhost', ['127.0.0.1@lo'], hdlr=self.eh)
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

        # Callback checks
        self.assert_events('server', "load modules", ['start', 'done'])
        result = self.eh.result('server', "load modules", 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('server', 'load modules', 'start', self.srv,
                         "load module 'lustre'")

        # Status check
        self.assertEqual(sorted(self.srv.modules.keys()), ['libcfs', 'lustre'])
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_module_load_dryrun(self):
        """Load lustre modules in dry-run mode"""
        act = self.srv.load_modules(dryrun=True)
        text = 'modprobe lustre'
        self.check_dryrun(act, text, 'server', 'load modules',
                          ['start', 'done'], self.srv, "load module 'lustre'")
        self.assertEqual(sorted(self.srv.modules.keys()), [])

    @Utils.rootonly
    def test_module_load_custom(self):
        """Load a custom module is ok"""
        act = self.srv.load_modules(modname='ldiskfs')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('server', "load modules", ['start', 'done'])
        result = self.eh.result('server', "load modules", 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('server', 'load modules', 'done', self.srv,
                         "load module 'ldiskfs'")

        # Status check
        self.assertEqual(self.srv.modules.keys(), ['ldiskfs'])
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_module_load_error(self):
        """Load a bad module is an error"""
        act = self.srv.load_modules(modname='ERROR')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('server', "load modules", ['start', 'failed'])
        result = self.eh.result('server', "load modules", 'failed')
        self.assertEqual(result.retcode, 1)
        self.assert_info('server', 'load modules', 'failed', self.srv,
                         "load module 'ERROR'")

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

        # Callback checks
        self.assert_events('server', "load modules", ['start', 'done'])
        result = self.eh.result('server', "load modules", 'done')
        self.assertEqual(str(result), "'lustre' is already loaded")
        self.assertEqual(result.retcode, None)
        self.assert_info('server', 'load modules', 'start', self.srv,
                         "load module 'lustre'")

        # Status check
        self.assertEqual(sorted(self.srv.modules.keys()), ['libcfs', 'lustre'])
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_module_unload(self):
        """Unload modules"""
        # First load modules
        self.srv.load_modules().launch()
        self.fs._run_actions()
        self.eh.clear()

        act = self.srv.unload_modules()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('server', 'unload modules', ['start', 'done'])
        result = self.eh.result('server', 'unload modules', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('server', 'unload modules', 'start', self.srv,
                         'unload modules')

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

        # Callback checks
        self.assert_events('server', 'unload modules', ['start', 'done'])
        result = self.eh.result('server', 'unload modules', 'done')
        self.assertEqual(str(result), 'modules already unloaded')
        self.assertEqual(result.retcode, None)
        self.assert_info('server', 'unload modules', 'done', self.srv,
                         'unload modules')

        # Status check
        self.assertEqual(self.srv.modules, {})
        self.assertEqual(act.status(), ACT_OK)


class ClientActionTest(CommonTestCase):

    def start(self):
        self.mdt.format().launch()
        self.ost.format().launch()
        self.mgs.format().launch()
        self.fs._run_actions()
        for tgt in (self.mgs, self.mdt, self.ost):
            tgt.lustre_check()
            tgt.start().launch()
            self.fs._run_actions()
        self.eh.clear()

    def setUp(self):
        nid = '%s@tcp' % Utils.HOSTNAME
        self.eh = self.ActionEH()
        self.fs = FileSystem('action', event_handler=self.eh)
        srv1 = Server(Utils.HOSTNAME, [nid], hdlr=self.eh)
        self.disk1 = Utils.make_disk()
        self.disk2 = Utils.make_disk()
        self.disk3 = Utils.make_disk()
        self.mgs = self.fs.new_target(srv1, 'mgt', 0, self.disk1.name)
        self.mdt = self.fs.new_target(srv1, 'mdt', 0, self.disk2.name)
        self.ost = self.fs.new_target(srv1, 'ost', 0, self.disk3.name)
        self.client = self.fs.new_client(srv1, '/mnt/lustre')

    def tearDown(self):
        # Umount client if mounted
        self.client.umount().launch()
        self.fs._run_actions()
        # Stop filesystem
        for tgt in (self.mdt, self.ost, self.mgs):
            tgt.stop().launch()
            self.fs._run_actions()

    #
    # Mount Client
    #
    @Utils.rootonly
    def test_mount_client_ok(self):
        """Mount a simple client"""
        self.start()
        act = self.client.mount()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'mount', ['start', 'done'])
        result = self.eh.result('comp', 'mount', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'mount', 'start', self.client,
                         'mount of action on /mnt/lustre')
        # Status checks
        self.assertEqual(self.client.state, MOUNTED)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_mount_client_dryrun(self):
        """Mount a client in dry-run mode"""
        self.start()
        act = self.client.mount(dryrun=True)
        text = 'mkdir -p "/mnt/lustre" && /bin/mount -t lustre ' \
               '%s@tcp:/action /mnt/lustre' % Utils.HOSTNAME
        self.check_dryrun(act, text, 'comp', 'mount', ['start', 'done'],
                          self.client, 'mount of action on /mnt/lustre')
        self.assertEqual(self.client.state, OFFLINE)

    @Utils.rootonly
    def test_mount_client_already_done(self):
        """Mount a client already mounted is ok"""
        self.start()

        self.client.mount().launch()
        self.fs._run_actions()
        self.eh.clear()

        # Try to mount it again
        act = self.client.mount()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'mount', ['start', 'done'])
        result = self.eh.result('comp', 'mount', 'done')
        self.assertEqual(result.retcode, None)
        self.assertEqual(str(result),
                         'action is already mounted on /mnt/lustre')
        self.assert_info('comp', 'mount', 'start', self.client,
                         'mount of action on /mnt/lustre')
        # Status checks
        self.assertEqual(self.client.state, MOUNTED)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_mount_client_failed(self):
        """Failed mount is correctly reported"""
        self.start()
        act = self.client.mount()
        def _prepare_cmd(_self):
            # Simulate mount returns ENOENT
            return ['exit 2']
        act._prepare_cmd = types.MethodType(_prepare_cmd, act)
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'mount', ['start', 'failed'])
        result = self.eh.result('comp', 'mount', 'failed')
        self.assertEqual(result.retcode, 2)
        self.assertEqual(str(result),
                         'No such file or directory')
        self.assert_info('comp', 'mount', 'failed', self.client,
                         'mount of action on /mnt/lustre')
        # Status checks
        self.assertEqual(self.client.state, OFFLINE)
        self.assertEqual(act.status(), ACT_ERROR)

    #
    # Unmount Client
    #
    @Utils.rootonly
    def test_umount_client_ok(self):
        """Umount a simple client"""
        self.start()
        self.client.mount().launch()
        self.fs._run_actions()
        self.eh.clear()

        act = self.client.umount()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'umount', ['start', 'done'])
        result = self.eh.result('comp', 'umount', 'done')
        self.assertEqual(result.retcode, 0)
        self.assert_info('comp', 'umount', 'start', self.client,
                         'umount of action on /mnt/lustre')
        # Status checks
        self.assertEqual(self.client.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_umount_client_dryrun(self):
        """Umount a client in dry-run mode"""
        self.start()
        self.client.mount().launch()
        self.fs._run_actions()
        self.eh.clear()

        act = self.client.umount(dryrun=True)
        text = 'umount /mnt/lustre'
        self.check_dryrun(act, text, 'comp', 'umount', ['start', 'done'],
                          self.client, 'umount of action on /mnt/lustre')
        self.assertEqual(self.client.state, MOUNTED)

    @Utils.rootonly
    def test_umount_client_already_done(self):
        """Umount a client already unmounted is ok"""
        # Do not start anything
        # Try to unmount
        act = self.client.umount()
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'umount', ['start', 'done'])
        result = self.eh.result('comp', 'umount', 'done')
        self.assertEqual(result.retcode, None)
        self.assertEqual(str(result),
                         'action is not mounted')
        self.assert_info('comp', 'umount', 'start', self.client,
                         'umount of action on /mnt/lustre')
        # Status checks
        self.assertEqual(self.client.state, OFFLINE)
        self.assertEqual(act.status(), ACT_OK)

    @Utils.rootonly
    def test_umount_client_failed(self):
        """Failed umount is correctly reported"""
        self.start()
        self.client.mount().launch()
        self.fs._run_actions()
        self.eh.clear()

        act = self.client.umount()
        def _prepare_cmd(_self):
            # Simulate umount returns ENOENT
            return ['exit 2']
        act._prepare_cmd = types.MethodType(_prepare_cmd, act)
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('comp', 'umount', ['start', 'failed'])
        result = self.eh.result('comp', 'umount', 'failed')
        self.assertEqual(result.retcode, 2)
        self.assertEqual(str(result),
                         'No such file or directory')
        self.assert_info('comp', 'umount', 'failed', self.client,
                         'umount of action on /mnt/lustre')
        # Status checks
        self.assertEqual(self.client.state, MOUNTED)
        self.assertEqual(act.status(), ACT_ERROR)


class TuneActionTest(CommonTestCase):

    def setUp(self):
        self.eh = self.ActionEH()
        self.fs = FileSystem('action', event_handler=self.eh)
        self.srv = Server('localhost', ['localhost@tcp'], hdlr=self.eh)
        self.disk = Utils.make_disk()
        self.tgt = self.fs.new_target(self.srv, 'mgt', 0, self.disk.name)
        self.model = TuningModel()
        self.model.create_parameter('/dev/null', 1, node_type_list=['mgs'])

    def test_tune_ok(self):
        """Apply simple tuning is ok"""
        # Create a working tuning
        self.assertEqual(len(self.model.get_params_for_name(None, ['mgs'])), 1)

        act = self.srv.tune(self.model, self.fs.components, 'action')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('server', 'tune', ['start', 'done'])
        self.assert_info('server', 'tune', 'start', self.srv, 'apply tunings')
        self.assert_info('server', 'tune', 'done', self.srv, 'apply tunings')

        # Status checks
        self.assertEqual(act.status(), ACT_OK)

    def test_tune_dryrun(self):
        """Apply tuning in dry-run mode"""
        act = self.srv.tune(self.model, self.fs.components, 'action',
                            dryrun=True)
        text = 'echo 1 > /dev/null'
        self.check_dryrun(act, text, 'server', 'tune', ['start', 'done'],
                          self.srv, 'apply tunings')

    def test_tune_error(self):
        """Apply a bad tuning is correctly reported"""
        # Add  bad tuning
        self.model.create_parameter('/proc/modules', 1, node_type_list=['mgs'])
        self.model.create_parameter('/proc/cmdline', 1, node_type_list=['mgs'])
        self.assertEqual(len(self.model.get_params_for_name(None, ['mgs'])), 3)

        act = self.srv.tune(self.model, self.fs.components, 'action')
        act.launch()
        self.fs._run_actions()

        # Callback checks
        self.assert_events('server', 'tune', ['start', 'failed'])
        result = self.eh.result('server', 'tune', 'failed')
        self.assertEqual(result.retcode, None)
        self.assertEqual(str(result),
                         "'echo 1 > /proc/modules' failed\n"
                         "'echo 1 > /proc/cmdline' failed")
        self.assert_info('server', 'tune', 'start', self.srv, 'apply tunings')
        self.assert_info('server', 'tune', 'failed', self.srv, 'apply tunings')

        # Status checks
        self.assertEqual(act.status(), ACT_ERROR)


class InstallActionTest(CommonTestCase):

    def setUp(self):
        self.eh = self.ActionEH()
        self.fs = FileSystem('action', event_handler=self.eh)
        nid = '%s@tcp' % Utils.HOSTNAME
        self.localname = Server(Utils.HOSTNAME, [nid], hdlr=self.eh).hostname
        self.badnames = Server('bad[1-15]', ['bad[1-15]@tcp'],
                               hdlr=self.eh).hostname

    def test_install_ok(self):
        """Install a simple file"""
        tmp = Utils.makeTempFile('')
        act = Install(self.localname, self.fs, tmp.name)
        act.launch()
        self.fs._run_actions()

        msgs = ['[COPY] %s on %s' % (tmp.name, self.localname),
                "Updating configuration file `%s' on %s" % \
                 (os.path.basename(tmp.name), self.localname)]
        self.assertEqual(self.eh.msglist, msgs)

        # Status checks
        self.assertEqual(act.status(), ACT_OK)

    def test_install_dryrun(self):
        """Install a file in dry-run mode"""
        tmp = Utils.makeTempFile("")
        act = Install(self.localname, self.fs, tmp.name, dryrun=True)
        self.mock_copy(act)
        act.launch()
        self.fs._run_actions()

        text = '[COPY] %s on %s' % (tmp.name, self.localname)
        self.assertEqual(self.eh.msglist[0], text)
        self.assertEqual(len(self.eh.msglist), 1)

        # Status checks
        self.assertEqual(act.status(), ACT_OK)

    def test_install_bad_file(self):
        """Install a non-existent file is corrected reported"""
        act = Install(self.localname, self.fs, '/bad/file')
        act.launch()
        self.fs._run_actions()

        text = '[COPY] /bad/file on %s' % self.localname
        self.assertEqual(self.eh.msglist[0], text)
        text = "Updating configuration file `file' on %s" % self.localname
        self.assertEqual(self.eh.msglist[1], text)
        self.assertEqual(len(self.eh.msglist), 2)

        # Status checks
        self.assertEqual(act.status(), ACT_ERROR)

    def test_install_bad_nodes(self):
        """Install to a bad node is corrected reported"""
        tmp = Utils.makeTempFile("")
        act = Install(self.badnames, self.fs, tmp.name)
        act.launch()
        self.fs._run_actions()

        text = '[COPY] %s on %s' % (tmp.name, self.badnames)
        self.assertEqual(self.eh.msglist[0], text)
        text = "Updating configuration file `%s' on %d servers" % \
            (os.path.basename(tmp.name), len(self.badnames))
        self.assertEqual(self.eh.msglist[1], text)
        self.assertEqual(len(self.eh.msglist), 2)

        # Status checks
        self.assertEqual(act.status(), ACT_ERROR)
