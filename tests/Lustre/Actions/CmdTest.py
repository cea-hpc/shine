#!/usr/bin/env python
#
# Copyright (C) 2007-2015 CEA
#
# Shine.Lustre.Actions.* test suite
#

"""Unit test for various Actions"""

import os
import unittest
import Utils

from Shine.Configuration.Globals import Globals
from Shine.Lustre.Server import Server, NodeSet
from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Actions.StartRouter import StartRouter
from Shine.Lustre.Actions.StopRouter import StopRouter
from Shine.Lustre.Actions.StartClient import StartClient
from Shine.Lustre.Actions.StopClient import StopClient
from Shine.Lustre.Actions.StartTarget import StartTarget
from Shine.Lustre.Actions.StopTarget import StopTarget
from Shine.Lustre.Actions.Fsck import Fsck
from Shine.Lustre.Actions.Format import JournalFormat, Format, Tunefs
from Shine.Lustre.Actions.Execute import Execute
from Shine.Lustre.Actions.Proxy import FSProxyAction

class ActionsTest(unittest.TestCase):

    def setUp(self):
        self.fs = FileSystem('action')
        self.srv1 = Server("localhost", ["localhost@tcp"])
        self.srv2 = Server("localhost2", ["localhost2@tcp"])
        self.block1 = Utils.get_block_dev(0)
        self.block2 = Utils.get_block_dev(1)

    def tearDown(self):
        del Globals()['lustre_version']

    def check_cmd(self, action, cmdline):
        """Check `action' prepare_cmd() return the provided cmdline."""
        self.assertEqual(' '.join(action._prepare_cmd()), cmdline)

    #
    # Router
    #

    def test_start_router(self):
        """test command line start router"""
        rtr = self.fs.new_router(self.srv1)
        action = StartRouter(rtr)
        self.assertEqual(sorted(action.needed_modules()), [])
        self.check_cmd(action, "/sbin/modprobe ptlrpc")

    def test_stop_router(self):
        """test command line stop router"""
        rtr = self.fs.new_router(self.srv1)
        action = StopRouter(rtr)
        self.check_cmd(action, "lustre_rmmod")

    #
    # Client
    #

    def test_start_client_simple(self):
        """test command line start client (mgs one nid)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client)
        self.assertEqual(sorted(action.needed_modules()), ['lustre'])
        self.check_cmd(action, 'mkdir -p "/foo" && ' +
                             '/bin/mount -t lustre localhost@tcp:/action /foo')

    def test_start_client_two_nids(self):
        """test command line start client (mgs two nids)"""
        srv = Server('localhost', ['localhost@tcp', 'localhost@o2ib'])
        self.fs.new_target(srv, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "/foo" && ' +
              '/bin/mount -t lustre localhost@tcp,localhost@o2ib:/action /foo')

    def test_start_client_mgs_failover(self):
        """test command line start client (mgs failover)"""
        mgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        mgt.add_server(self.srv2)
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "/foo" && ' +
              '/bin/mount -t lustre localhost@tcp:localhost2@tcp:/action /foo')

    def test_start_client_mount_options(self):
        """test command line start client (mount options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo", mount_options="acl")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "/foo" && ' +
                      '/bin/mount -t lustre -o acl localhost@tcp:/action /foo')

    def test_start_client_subdir(self):
        """test command line start client (subdir)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo", subdir="projects")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "/foo" && ' +
                    '/bin/mount -t lustre localhost@tcp:/action/projects /foo')

    def test_start_client_addl_options(self):
        """test command line start client (addl options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client, addopts='user_xattr')
        self.check_cmd(action, 'mkdir -p "/foo" && ' +
               '/bin/mount -t lustre -o user_xattr localhost@tcp:/action /foo')

    def test_start_client_both_options(self):
        """test command line start client (both options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo", mount_options="acl")
        action = StartClient(client, addopts='user_xattr')
        self.check_cmd(action, 'mkdir -p "/foo" && ' +
           '/bin/mount -t lustre -o acl,user_xattr localhost@tcp:/action /foo')

    def test_startstop_client_custom_vars(self):
        """test command line start/stop client (custom vars)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        # fs_name
        mtpt = '/action'
        client = self.fs.new_client(self.srv1, "/$fs_name")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "%s" && ' \
               '/bin/mount -t lustre localhost@tcp:/action %s' % (mtpt, mtpt))
        action = StopClient(client)
        self.check_cmd(action, 'umount %s' % mtpt)
        # label
        mtpt = '/action-client'
        client = self.fs.new_client(self.srv1, "/$label")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "%s" && ' \
               '/bin/mount -t lustre localhost@tcp:/action %s' % (mtpt, mtpt))
        action = StopClient(client)
        self.check_cmd(action, 'umount %s' % mtpt)
        # type
        mtpt = '/client'
        client = self.fs.new_client(self.srv1, "/client")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "%s" && ' \
               '/bin/mount -t lustre localhost@tcp:/action %s' % (mtpt, mtpt))
        action = StopClient(client)
        self.check_cmd(action, 'umount %s' % mtpt)

    def test_stop_client_simple(self):
        """test command line stop client (simple)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo")
        action = StopClient(client)
        self.check_cmd(action, 'umount /foo')

    def test_stop_client_addopts(self):
        """test command line stop client (addl opts)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo")
        action = StopClient(client, addopts='-f')
        self.check_cmd(action, 'umount -f /foo')


    #
    # Target
    #

    def test_fsck(self):
        """test command line fsck"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = Fsck(tgt)
        self.check_cmd(action, 'e2fsck -f -C2 %s -y' % self.block1)

    def test_fsck_addopts(self):
        """test command line fsck (addl options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = Fsck(tgt, addopts='-v')
        self.check_cmd(action, 'e2fsck -f -C2 %s -v' % self.block1)

    def test_fsck_addopts_placeholders(self):
        """test command line fsck (addl options with placeholders)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = Fsck(tgt, addopts='--ostdb /mnt/db/%label.db')
        self.check_cmd(action,
                'e2fsck -f -C2 %s --ostdb /mnt/db/MGS.db' % self.block1)

    # XXX: All full_check() calls should be replaced by a real call to the
    # method dedicated action for the Target.

    def test_start_target_modules_v2_1x(self):
        Globals().replace('lustre_version', '2.1')
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = StartTarget(tgt)
        self.assertEqual(sorted(action.needed_modules()),
                          ['ldiskfs', 'lustre'])

    def test_start_target_modules_v2_4x(self):
        Globals().replace('lustre_version', '2.4')
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = StartTarget(tgt)
        self.assertEqual(sorted(action.needed_modules()),
                          ['fsfilt_ldiskfs', 'lustre'])

    def test_start_target_modules_v2_5x(self):
        Globals().replace('lustre_version', '2.5')
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = StartTarget(tgt)
        self.assertEqual(sorted(action.needed_modules()),
                          ['ldiskfs', 'lustre'])

    def test_start_target(self):
        """test command line start target"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt)
        self.check_cmd(action,
                'mkdir -p "/mnt/action/mgt/0" && ' +
                '/bin/mount -t lustre %s /mnt/action/mgt/0' % self.block1)

    def test_start_target_addopts(self):
        """test command line start target (addl options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt, addopts='abort_recov')
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && ' +
               '/bin/mount -t lustre -o abort_recov %s /mnt/action/mgt/0' % self.block1)

    def test_start_target_mount_options(self):
        """test command line start target (mount_options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt, mount_options={'mgt': 'abort_recov'})
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && ' +
               '/bin/mount -t lustre -o abort_recov %s /mnt/action/mgt/0' % self.block1)

    def test_start_target_mount_options_none(self):
        """test command line start target (mount_options missing)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt, mount_options={'mdt': 'abort_recov'})
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && ' +
               '/bin/mount -t lustre %s /mnt/action/mgt/0' % self.block1)

        action = StartTarget(tgt, mount_options={'mgt': None})
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && ' +
               '/bin/mount -t lustre %s /mnt/action/mgt/0' % self.block1)

    def test_start_target_both_options(self):
        """test command line start target (both options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt, addopts='ro',
                             mount_options={'mgt': 'abort_recov'})
        self.check_cmd(action,
             'mkdir -p "/mnt/action/mgt/0" && ' +
             '/bin/mount -t lustre -o abort_recov,ro %s /mnt/action/mgt/0' % self.block1)

    def test_start_target_jdev(self):
        """test command line start target (with journal)"""
        dev = self.block1
        jdev = self.block2
        majorminor = os.stat(jdev).st_rdev

        tgt = self.fs.new_target(self.srv1, 'mgt', 0, dev, jdev)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt)
        self.check_cmd(action,
          'mkdir -p "/mnt/action/mgt/0" && ' +
          '/bin/mount -t lustre -o journal_dev=%#x %s /mnt/action/mgt/0' %
          (majorminor, dev))

    def test_start_target_file_device(self):
        """test command line start target (file device)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/etc/passwd')
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt)
        self.check_cmd(action,
                'mkdir -p "/mnt/action/mgt/0" && ' +
                '/bin/mount -t lustre -o loop /etc/passwd /mnt/action/mgt/0')

    def test_start_target_mount_paths(self):
        """test command line start target (mount paths)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/mypath'})
        self.check_cmd(action,
                'mkdir -p "/mnt/mypath" && ' +
                '/bin/mount -t lustre %s /mnt/mypath' % self.block1)

    def test_start_target_custom_mount_paths(self):
        """test command line start target (custom mount paths)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)

        # fs_name
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$fs_name/mgt'})
        self.check_cmd(action,
                'mkdir -p "/mnt/action/mgt" && ' +
                '/bin/mount -t lustre %s /mnt/action/mgt' % self.block1)
        # index
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/mgt/$index'})
        self.check_cmd(action,
                'mkdir -p "/mnt/mgt/0" && ' +
                '/bin/mount -t lustre %s /mnt/mgt/0' % self.block1)
        # type
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$type/$index'})
        self.check_cmd(action,
                'mkdir -p "/mnt/mgt/0" && ' +
                '/bin/mount -t lustre %s /mnt/mgt/0' % self.block1)
        # label
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$label'})
        self.check_cmd(action, 'mkdir -p "/mnt/MGS"' +
                               ' && /bin/mount -t lustre %s /mnt/MGS' % self.block1)
        # dev
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$fs_name-$dev'})
        loopname = self.block1[self.block1.rindex('/') + 1:]
        self.check_cmd(action, 'mkdir -p "/mnt/action-%s"' % loopname +
                        ' && /bin/mount -t lustre %s /mnt/action-%s' % (self.block1, loopname))
        # No jdev
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$fs_name-$jdev'})
        self.check_cmd(action, 'mkdir -p "/mnt/action-$jdev"' +
                        ' && /bin/mount -t lustre %s /mnt/action-$jdev' % self.block1)

        # Bad variable, leave it as-is
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$bad'})
        self.check_cmd(action,
                'mkdir -p "/mnt/$bad" && ' +
                '/bin/mount -t lustre %s /mnt/$bad' % self.block1)

        # jdev
        dirname = self.block2[self.block2.rfind('/')+1:]
        majorminor = os.stat(self.block2).st_rdev
        tgt = self.fs.new_target(self.srv1, 'mdt', 0, self.block1, self.block2)
        tgt.full_check(mountdata=False)
        action = StartTarget(tgt, mount_paths={'mdt': '/mnt/$jdev'})
        self.check_cmd(action, 'mkdir -p "/mnt/%s" && ' % dirname +
              '/bin/mount -t lustre -o journal_dev=%#x ' % majorminor +
              '%s /mnt/%s' % (self.block1, dirname))

    # Stop
    def test_stop_target(self):
        """test command line stop target"""
        dev = self.block1
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, dev)
        tgt.full_check(mountdata=False)
        action = StopTarget(tgt)
        self.check_cmd(action, 'umount %s' % dev)

    def test_stop_target_addopts(self):
        """test command line stop target (addl options)"""
        dev = self.block1
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, dev)
        tgt.full_check(mountdata=False)
        action = StopTarget(tgt, addopts='-l')
        self.check_cmd(action, 'umount -l %s' % dev)

    def test_stop_target_file_device(self):
        """test command line stop target (file device)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/etc/passwd')
        tgt.full_check(mountdata=False)
        action = StopTarget(tgt)
        self.check_cmd(action, 'umount -d /etc/passwd')

    # Format
    def check_cmd_format(self, action, cmdline):
        """Helper method to check cmdline for format actions"""
        self.check_cmd(action,
                 'mkfs.lustre --reformat --quiet "--fsname=action" ' + cmdline)

    def test_format_target(self):
        """test command line format (MGT)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        self.assertEqual(sorted(action.needed_modules()), ['ldiskfs'])
        self.check_cmd_format(action, '--mgs %s' % self.block1)

    def test_format_target_loopback(self):
        """test command line format (MGT in loopback)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/etc/passwd')
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        size = os.stat('/etc/passwd').st_size / 1024
        self.check_cmd_format(action, '--mgs --device-size=%d /etc/passwd' %
                size)

    def test_format_target_jdev(self):
        """test command line format (MGT with jdev and mkfsoptions)"""
        jdev = self.block2
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1, jdev)
        tgt.full_check(mountdata=False)
        action = Format(tgt, mkfs_options={'mgt': '-m 2'})
        jaction = JournalFormat(tgt.journal)
        self.check_cmd(jaction, 'mke2fs -q -F -O journal_dev -b 4096 %s' % jdev)
        self.check_cmd_format(action, '--mgs '
                        '"--mkfsoptions=-j -J device=%s -m 2" %s' % (jdev, self.block1))

    def test_format_target_mdt(self):
        """test command line format (MDT)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--mdt --index=0 ' +
                              '"--mgsnode=localhost@tcp" %s' % self.block1)

    def test_format_target_mdt_options(self):
        """test command line format (MDT with addl options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, addopts='-v')
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" -v %s' % self.block1)

    def test_format_target_mdt_quota_v1x(self):
        """test command line format v1.x (MDT with quota)"""
        Globals().replace('lustre_version', '1.6')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, quota=True, quota_type='ug')
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" "--param=mdt.quota_type=ug" %s' % self.block1)

    def test_format_target_mdt_quota_v2x(self):
        """test command line format v2.x (MDT with quota)"""
        Globals().replace('lustre_version', '2.0.0.1')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, quota=True, quota_type='ug')
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" "--param=mdd.quota_type=ug" %s' % self.block1)

    def test_format_target_mdt_quota_v24(self):
        """test command line format v2.4 and above (MDT with quota)"""
        Globals().replace('lustre_version', '2.4')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, quota=True, quota_type='ug')
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" %s' % self.block1)

    def test_format_target_mdt_striping(self):
        """test command line format (MDT with striping)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, stripecount=2, stripesize=2097152)
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" --param=lov.stripecount=2 ' +
             '--param=lov.stripesize=2097152 %s' % self.block1)

    def test_format_target_mdt_mkfsoptions(self):
        """test command line format (MDT with mkfsoptions)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, mkfs_options={'mdt': '-m 2'})
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" "--mkfsoptions=-m 2" %s' % self.block1)

    def test_format_target_mdt_param(self):
        """test command line format (MDT with param)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, format_params={'mdt': 'foo'})
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" "--param=foo" %s' % self.block1)

    def test_format_target_ost(self):
        """test command line format (OST)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'ost', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
                              '"--mgsnode=localhost@tcp" %s' % self.block1)

    def test_format_target_ost_quota_v2x(self):
        """test command line format v2.x (OST with quota)"""
        Globals().replace('lustre_version', '2.0.0.1')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'ost', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, quota=True, quota_type='ug')
        self.check_cmd_format(action, '--ost --index=0 ' +
             '"--mgsnode=localhost@tcp" "--param=ost.quota_type=ug" %s' % self.block1)

    def test_format_target_ost_quota_v24(self):
        """test command line format v2.4 and above (OST with quota)"""
        Globals().replace('lustre_version', '2.4')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv2, 'ost', 0, self.block1)
        tgt.full_check(mountdata=False)
        action = Format(tgt, quota=True, quota_type='ug')
        self.check_cmd_format(action, '--ost --index=0 ' +
             '"--mgsnode=localhost@tcp" %s' % self.block1)

    def test_format_target_ost_failnode(self):
        """test command line format (OST with failnode)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv1, 'ost', 0, self.block1)
        tgt.add_server(self.srv2)
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
             '"--mgsnode=localhost@tcp" "--failnode=localhost2@tcp" %s' % self.block1)

    def test_format_target_ost_two_failnodes(self):
        """test command line format (OST with 2 failnodes)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv1, 'ost', 0, self.block1)
        tgt.add_server(self.srv2)
        tgt.add_server(Server('localhost3', ['localhost3@tcp']))
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
             '"--mgsnode=localhost@tcp" "--failnode=localhost2@tcp" ' +
             '"--failnode=localhost3@tcp" %s' % self.block1)

    def test_format_target_ost_bad_network(self):
        """test command line format (OST with a bad network)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv1, 'ost', 0, self.block1, network='bad netw')
        tgt.add_server(self.srv2)
        action = Format(tgt)
        self.assertRaises(ValueError, action._prepare_cmd)

    def test_format_target_ost_failnodes_network(self):
        """test command line format (OST with 2 failnodes and network)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv1, 'ost', 0, self.block1, network='tcp')
        tgt.add_server(self.srv2)
        tgt.add_server(Server('localhost3', ['localhost3@o2ib']))
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
          '"--mgsnode=localhost@tcp" "--failnode=localhost2@tcp" ' +
          '--network=tcp %s' % self.block1)

    def test_format_target_network_zero(self):
        """test command line format (network with zero suffix)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        tgt = self.fs.new_target(self.srv1, 'ost', 0, self.block1, network='o2ib0')
        tgt.add_server(self.srv2)
        tgt.add_server(Server('localhost3', ['localhost3@o2ib']))
        tgt.full_check(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
          '"--mgsnode=localhost@tcp" "--failnode=localhost3@o2ib" ' +
          '--network=o2ib0 %s' % self.block1)

    # Tunefs
    def check_cmd_tunefs(self, action, cmdline):
        """Helper method to check cmdline for tunefs actions"""
        self.check_cmd(action,
                 'tunefs.lustre --erase-params --quiet ' + cmdline)

    def test_tunefs_mgs_writeconf(self):
        """test command line tunefs writeconf (MGT)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = Tunefs(tgt, writeconf=True)
        self.assertEqual(sorted(action.needed_modules()), ['ldiskfs'])
        self.check_cmd_tunefs(action, '--writeconf %s' % self.block1)

    def test_tunefs_mgs_addl(self):
        """test command line tunefs addl options (MGT)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = Tunefs(tgt, addopts='-v')
        self.check_cmd_tunefs(action, '-v %s' % self.block1)

    def test_tunefs_mdt(self):
        """test command line tunefs (MDT)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, self.block1)
        action = Tunefs(mdt)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" %s' % self.block1)

    def test_tunefs_ost(self):
        """test command line tunefs (OST)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, self.block1)
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" %s' % self.block1)

    def test_tunefs_mdt_striping(self):
        """test command line tunefs striping (MDT)"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, self.block1)
        action = Tunefs(mdt, stripecount=2, stripesize=2097152)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '--param=lov.stripecount=2 ' +
                              '--param=lov.stripesize=2097152 %s' % self.block1)

    def test_tunefs_target_quota_v1x(self):
        """test command line tunefs quota (v1.x)"""
        Globals().replace('lustre_version', '1.6')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, self.block1)
        action = Tunefs(mdt, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=mdt.quota_type=ug" %s' % self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/sdb')
        action = Tunefs(ost, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=ost.quota_type=ug" /dev/sdb')

    def test_tunefs_target_quota_v2x(self):
        """test command line tunefs quota (v2.x)"""
        Globals().replace('lustre_version', '2.0.0.1')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, self.block1)
        action = Tunefs(mdt, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=mdd.quota_type=ug" %s' % self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/sdb')
        action = Tunefs(ost, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=ost.quota_type=ug" /dev/sdb')

    def test_tunefs_target_quota_v24(self):
        """test command line tunefs quota (v2.4 and above)"""
        Globals().replace('lustre_version', '2.4')
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, self.block1)
        action = Tunefs(mdt, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/sdb')
        action = Tunefs(ost, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '/dev/sdb')

    def test_tunefs_target_failnode(self):
        """test command line tunefs failnode"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, self.block1)
        ost.add_server(self.srv2)
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--failnode=localhost2@tcp" %s' % self.block1)

    def test_tunefs_target_network(self):
        """test command line tunefs network"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, self.block1, network='tcp')
        ost.add_server(self.srv2)
        ost.add_server(Server('localhost3', ['localhost3@o2ib']))
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                           '"--failnode=localhost2@tcp" --network=tcp %s' % self.block1)

    def test_tunefs_target_network_zero(self):
        """test command line tunefs network with zero suffix"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, self.block1, network='o2ib0')
        ost.add_server(self.srv2)
        ost.add_server(Server('localhost3', ['localhost3@o2ib']))
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                           '"--failnode=localhost3@o2ib" --network=o2ib0 %s' % self.block1)

    def test_tunefs_target_network_zero2(self):
        """test command line tunefs network without zero suffix"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, self.block1, network='o2ib')
        ost.add_server(self.srv2)
        ost.add_server(Server('localhost3', ['localhost3@o2ib0']))
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                           '"--failnode=localhost3@o2ib0" --network=o2ib %s' % self.block1)

    def test_tunefs_target_network_zero3(self):
        """test command line tunefs network with non-zero suffix"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, self.block1, network='o2ib1')
        ost.add_server(self.srv2)
        ost.add_server(Server('localhost3', ['localhost3@o2ib1']))
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                           '"--failnode=localhost3@o2ib1" --network=o2ib1 %s' % self.block1)

    def test_tunefs_target_format_params(self):
        """test command line tunefs format params"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        ost = self.fs.new_target(self.srv1, 'ost', 0, self.block1)
        action = Tunefs(ost, format_params={'ost': 'foo'})
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=foo" %s' % self.block1)

    # Execute

    def test_simple_execute(self):
        """test simple execute"""
        mgs = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = Execute(mgs, addopts="foo")
        self.check_cmd(action, "foo")

    def test_execute_target(self):
        """test execute with target fields"""
        mgs = self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        action = Execute(mgs, addopts="fsck %device")
        self.check_cmd(action, 'fsck %s' % self.block1)

    def test_execute_client(self):
        """test execute with client fields"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo", "ro", "home")
        action = Execute(client, addopts="mount %mntpath %mntopts %subdir")
        self.check_cmd(action, "mount /foo ro home")

    def test_execute_client_bad_fields(self):
        """test execute with client and dev fields"""
        self.fs.new_target(self.srv1, 'mgt', 0, self.block1)
        client = self.fs.new_client(self.srv1, "/foo")
        action = Execute(client, addopts="mount %device")
        self.check_cmd(action, "mount ")

    def test_execute_router(self):
        """test execute with router fields"""
        rtr = self.fs.new_router(self.srv1)
        action = Execute(rtr, addopts="start %fsname")
        self.check_cmd(action, "start action")

    #
    # Proxy
    #

    def _create_proxy(self, **kwargs):
        """Instanciate a FSProxyAction."""
        return FSProxyAction(self.fs, 'dummy', 'foo', **kwargs)

    def test_simple_proxy(self):
        """test proxy with minimal arguments"""
        action = self._create_proxy(debug=False)
        self.check_cmd(action, 'shine dummy -f action -R')

    def test_proxy_debug(self):
        """test proxy with debug"""
        action = self._create_proxy(debug=True)
        self.check_cmd(action, 'shine dummy -f action -R -d')

    def test_proxy_comps(self):
        """test proxy with a component list"""
        self.fs.new_router(self.srv1)
        self.fs.new_client(self.srv1, "/foo")
        action = self._create_proxy(debug=False, comps=self.fs.components)
        self.check_cmd(action, 'shine dummy -f action -R'
                               ' -l action-client,action-router')

    def test_proxy_comps_addopts(self):
        """test proxy with a component list and additional options"""
        self.fs.new_router(self.srv1)
        self.fs.new_client(self.srv1, "/foo")
        action = self._create_proxy(debug=False, comps=self.fs.components,
                                    addopts="-y")
        self.check_cmd(action, "shine dummy -f action -R"
                               " -l action-client,action-router -o '-y'")

    def test_proxy_comps_failover(self):
        """test proxy with a component list and failover"""
        self.fs.new_router(self.srv1)
        self.fs.new_client(self.srv1, "/foo")
        action = self._create_proxy(debug=False, comps=self.fs.components,
                                    failover=NodeSet('failnode'))
        self.check_cmd(action, "shine dummy -f action -R"
                               " -l action-client,action-router -F 'failnode'")

    def test_proxy_comps_mountdata_never(self):
        """test proxy with a component list and mountdata=never"""
        action = self._create_proxy(debug=False, mountdata='never')
        self.check_cmd(action, "shine dummy -f action -R"
                               " --mountdata=never")

    def test_proxy_comps_mountdata_auto(self):
        """test proxy with a component list and mountdata=auto"""
        action = self._create_proxy(debug=False, mountdata='auto')
        self.check_cmd(action, "shine dummy -f action -R")

    def test_proxy_fanout(self):
        """test proxy with fanout"""
        action = self._create_proxy(debug=False, fanout=18)
        self.check_cmd(action, 'shine dummy -f action -R --fanout=18')

    def test_proxy_dryrun(self):
        """test proxy with dryrun"""
        action = self._create_proxy(debug=False, dryrun=True)
        self.check_cmd(action, 'shine dummy -f action -R --dry-run')
