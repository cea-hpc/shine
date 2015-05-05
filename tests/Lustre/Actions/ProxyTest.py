# test suite for launch() method in Shine.Lustre.Actions.*
# Copyright (C) 2015 CEA
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

from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Component import MOUNTED, OFFLINE, RUNTIME_ERROR
from Shine.Lustre.Server import Server
from Shine.Lustre.Actions.Action import ACT_OK, ACT_ERROR
from Shine.Lustre.Actions.StartTarget import StartTarget

from Shine.Lustre.Actions.Proxy import shine_msg_pack, SHINE_MSG_MAGIC, \
                                       SHINE_MSG_VERSION

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
        """send a done message which fails update due to bad property"""
        msg = shine_msg_pack(evtype='comp', info=self.info, status='done')
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

    def test_compat_msg_v2(self):
        """message shine version 2 is compatible"""
        class CustomEH(EventHandler):
            def __init__(eh):
                EventHandler.__init__(eh)
                eh.event = None
            def event_callback(eh, evtype, **kwargs):
                if kwargs['info'].actname != 'proxy':
                    self.assertEqual(eh.event, None)
                    eh.event = kwargs

        # v2-style message:
        # comp=mgt, action=start, status=failed, rc=1, message='fake error'
        msg = "SHINE:2:ev_starttarget_failed:gAJ9cQAoVQRjb21wcQFjU2hpbmUuTHV" \
              "zdHJlLlRhcmdldApNR1QKcQIpgXEDfXEEKFUNZGVmYXVsdHNlcnZlcnEFY1No" \
              "aW5lLkx1c3RyZS5TZXJ2ZXIKU2VydmVyCnEGKYFxB31xCChVBG5pZHNxCV1xC" \
              "lUIZm9vQHRjcDBxC2FVCGhvc3RuYW1lcQxjQ2x1c3RlclNoZWxsLk5vZGVTZX" \
              "QKTm9kZVNldApxDSmBcQ59cQ8oVQhfdmVyc2lvbnEQSwJVCV9hdXRvc3RlcHE" \
              "RTlUHX2xlbmd0aHESSwBVCV9wYXR0ZXJuc3ETfXEUVQNmb29xFU5zdWJ1YlUG" \
              "bW50ZGV2cRZVCC9kZXYvc2R6cRdVA3RhZ3EYTlUbX0NvbXBvbmVudF9fcnVub" \
              "mluZ19hY3Rpb25zcRldcRpVC3N0YXR1c19pbmZvcRtOVQVpbmRleHEcSwBVDm" \
              "FjdGlvbl9lbmFibGVkcR2IVQpsZGRfc3ZuYW1lcR5OVQVncm91cHEfTlUHbmV" \
              "0d29ya3EgTlUKX2xkZF9mbGFnc3EhSwBVBV9tb2RlcSJVB21hbmFnZWRxI1UJ" \
              "ZGV2X2lzYmxrcSSJVQNkZXZxJWgXVQZzZXJ2ZXJxJmgHVQpsZGRfZnNuYW1lc" \
              "SdOVQVzdGF0ZXEoTlUEamRldnEpTlUIZGV2X3NpemVxKksAVQtmYWlsc2Vydm" \
              "Vyc3ErY1NoaW5lLkx1c3RyZS5TZXJ2ZXIKU2VydmVyR3JvdXAKcSwpgXEtfXE" \
              "uVQVfbGlzdHEvXXEwc2J1YlUHbWVzc2FnZXExVQpmYWtlIGVycm9ycTJVAnJj" \
              "cTNLAXUu"
        self.fs.hdlr = CustomEH()
        self.act.fakecmd = 'echo "%s"' % msg
        self.act.launch()
        self.fs._run_actions()

        self.assertEqual(self.fs.hdlr.event['info'].actname, 'start')
        self.assertEqual(self.fs.hdlr.event['status'], 'failed')
        self.assertEqual(self.fs.hdlr.event['result'].retcode, 1)
        self.assertEqual(self.fs.hdlr.event['result'].message, 'fake error')

        self.fs._check_errors([OFFLINE], self.fs.components)
        self.assertEqual(len(self.fs.proxy_errors), 0)
        self.assertEqual(self.act.status(), ACT_OK)
