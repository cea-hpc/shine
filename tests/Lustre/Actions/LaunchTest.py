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

import types
import unittest
import binascii
import Utils

from Shine.Configuration.TuningModel import TuningModel

from Shine.Lustre.Actions.Action import ACT_OK, ACT_ERROR
from Shine.Lustre.Actions.StartTarget import StartTarget
from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.Server import Server
from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Component import MOUNTED, OFFLINE, TARGET_ERROR, RUNTIME_ERROR

from Shine.Lustre.Actions.Proxy import shine_msg_pack, SHINE_MSG_MAGIC, \
                                       SHINE_MSG_VERSION

class CommonTestCase(unittest.TestCase):

    class ActionEH(EventHandler):
        def __init__(self):
            EventHandler.__init__(self)
            self.evlist = dict()

        def event_callback(self, evtype, **kwargs):
            status = kwargs.get('status')
            action = kwargs.get('info').actname
            self.evlist['%s_%s_%s' % (evtype, action, status)] = kwargs

        def clear(self):
            self.evlist.clear()

        def result(self, evtype, action, status, key='result'):
            evname = '%s_%s_%s' % (evtype, action, status)
            return self.evlist[evname][key]

    def assert_events(self, evtype, action, status_list):
        evset = set(('%s_%s_%s' % (evtype, action, status)
                     for status in status_list))
        raisedset = set(self.eh.evlist.keys())
        self.assertEqual(evset, raisedset)

    def assert_info(self, evtype, action, status, elem, text):
        info = self.eh.result(evtype, action, status, key='info')
        self.assertEqual(info.elem, elem)
        self.assertEqual(str(info), text)

    def setUp(self):
        self.eh = self.ActionEH()

class ActionsTest(CommonTestCase):

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


class TuneActionTest(CommonTestCase):

    def setUp(self):
        self.fs = FileSystem('action')
        self.srv = Server('localhost', ['localhost@tcp'])
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

        # Status checks
        self.assertEqual(act.status(), ACT_OK)

    def test_tune_error(self):
        """Apply a bad tuning is correctly reported"""
        # Add  bad tuning
        self.model.create_parameter('/proc/modules', 1, node_type_list=['mgs'])
        self.model.create_parameter('/proc/cmdline', 1, node_type_list=['mgs'])
        self.assertEqual(len(self.model.get_params_for_name(None, ['mgs'])), 3)

        act = self.srv.tune(self.model, self.fs.components, 'action')
        act.launch()
        self.fs._run_actions()

        # Status checks
        self.assertEqual(act.status(), ACT_ERROR)


class ProxyTest(unittest.TestCase):

    def setUp(self):
        self.fs = FileSystem('proxy')
        self.srv1 = Server(Utils.HOSTNAME, ["%s@tcp" % Utils.HOSTNAME])
        disk = Utils.makeTempFilename()
        self.tgt = self.fs.new_target(self.srv1, 'mgt', 0, disk)

        self.act = self.fs._proxy_action('start', self.srv1.hostname,
                                         self.fs.components)
        self.info = StartTarget(self.tgt).info()
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
        self.assertEqual(list(self.fs.proxy_errors.messages())[0],
                         "Remote action start failed: No response")
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)
        self.assertEqual(self.act.status(), ACT_ERROR)

    def test_start_crash(self):
        """send a start message then crashes"""
        msg = shine_msg_pack(evtype='comp', info=self.info, status='start')

        self.act.fakecmd = 'echo "%s"; echo BAD; exit 1' % msg
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([MOUNTED], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 1)
        self.assertEqual(list(self.fs.proxy_errors.messages())[0],
                         "Remote action start failed: \nBAD\n")
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)
        self.assertEqual(self.act.status(), ACT_ERROR)

    def test_start_ok(self):
        """send a start and done message"""
        msgs = []
        msgs.append(shine_msg_pack(evtype='comp', info=self.info,
                                   status='start'))
        self.tgt.state = MOUNTED
        msgs.append(shine_msg_pack(evtype='comp', info=self.info,
                                   status='done'))

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
        msgs.append(shine_msg_pack(evtype='comp', info=self.info,
                                   status='start'))
        self.tgt.state = MOUNTED
        msgs.append(shine_msg_pack(evtype='comp', info=self.info,
                                   status='done'))

        self.act.fakecmd = 'echo "%s"; echo Oops; exit 1' % '\n'.join(msgs)
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([MOUNTED], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 1)
        self.assertEqual(list(self.fs.proxy_errors.messages())[0],
                         "Remote action start failed: \n\nOops\n")
        self.assertEqual(self.tgt.state, MOUNTED)
        self.assertEqual(self.act.status(), ACT_ERROR)

    def test_bad_object(self):
        """send a start message which fails update due to bad property"""
        msg = shine_msg_pack(evtype='comp', info=self.info, status='start')
        def buggy_update(self, other):
            self.wrong_property = other.wrong_property
        self.tgt.update = types.MethodType(buggy_update, self.tgt)

        self.act.fakecmd = 'echo "%s"' % msg
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([OFFLINE], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 1)
        self.assertEqual(str(list(self.fs.proxy_errors.messages())[0]),
                         "Cannot read message (check Shine and ClusterShell "
                         "version): 'MGT' object has no attribute "
                         "'wrong_property'")
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)
        self.assertEqual(self.act.status(), ACT_OK)

    def test_cannot_unpickle(self):
        """send a forged message which fails due to bad pickle content"""
        msg = "%s%d:%s" % (SHINE_MSG_MAGIC, SHINE_MSG_VERSION,
                           binascii.b2a_base64('bad content'))

        self.act.fakecmd = 'echo "%s"' % msg
        self.act.launch()
        self.fs._run_actions()
        self.fs._check_errors([OFFLINE], self.fs.components)

        self.assertEqual(len(self.fs.proxy_errors), 1)
        self.assertEqual(str(list(self.fs.proxy_errors.messages())[0]),
                         "Cannot unpickle message (check Shine and ClusterShell"
                         " versions): pop from empty list")
        self.assertEqual(self.tgt.state, RUNTIME_ERROR)
        self.assertEqual(self.act.status(), ACT_OK)

    def test_compat_compname(self):
        """message with compname value is backward compatible"""
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
