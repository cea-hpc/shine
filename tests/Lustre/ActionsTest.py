#!/usr/bin/env python
# Shine.Lustre.Actions.* test suite
# Written by A. Degremont 2010-12-19
# $Id$


"""Unit test for various Actions"""

import os
import unittest

from Shine.Lustre.Server import Server
from Shine.Lustre.FileSystem import FileSystem
from Shine.Lustre.Actions.StartRouter import StartRouter
from Shine.Lustre.Actions.StopRouter import StopRouter
from Shine.Lustre.Actions.StartClient import StartClient
from Shine.Lustre.Actions.StopClient import StopClient
from Shine.Lustre.Actions.StartTarget import StartTarget
from Shine.Lustre.Actions.StopTarget import StopTarget
from Shine.Lustre.Actions.Fsck import Fsck
from Shine.Lustre.Actions.Format import JournalFormat, Format, Tunefs

class ActionsTest(unittest.TestCase):

    def setUp(self):
        self.fs = FileSystem('action')
        self.srv1 = Server("localhost", ["localhost@tcp"])
        self.srv2 = Server("localhost2", ["localhost2@tcp"])

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
        self.check_cmd(action, "/sbin/modprobe lnet && lctl net up")

    def test_stop_router(self):
        """test command line stop router"""
        rtr = self.fs.new_router(self.srv1)
        action = StopRouter(rtr)
        self.check_cmd(action, "lctl net down && lustre_rmmod")

    #
    # Client
    #

    def test_start_client_simple(self):
        """test command line start client (mgs one nid)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "/foo" && /sbin/modprobe lustre && ' +
                             '/bin/mount -t lustre localhost@tcp:/action /foo')

    def test_start_client_two_nids(self):
        """test command line start client (mgs two nids)"""
        srv = Server('localhost', ['localhost@tcp','localhost@o2ib'])
        self.fs.new_target(srv, 'mgt', 0, '/dev/root')
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "/foo" && /sbin/modprobe lustre && ' +
              '/bin/mount -t lustre localhost@tcp,localhost@o2ib:/action /foo')

    def test_start_client_mgs_failover(self):
        """test command line start client (mgs failover)"""
        mgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        mgt.add_server(self.srv2)
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client)
        self.check_cmd(action, 'mkdir -p "/foo" && /sbin/modprobe lustre && ' +
              '/bin/mount -t lustre localhost@tcp:localhost2@tcp:/action /foo')

    def test_start_client_mount_options(self):
        """test command line start client (mount options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client, mount_options='acl')
        self.check_cmd(action, 'mkdir -p "/foo" && /sbin/modprobe lustre && ' +
                      '/bin/mount -t lustre -o acl localhost@tcp:/action /foo')

    def test_start_client_addl_options(self):
        """test command line start client (addl options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client, addopts='user_xattr')
        self.check_cmd(action, 'mkdir -p "/foo" && /sbin/modprobe lustre && ' +
               '/bin/mount -t lustre -o user_xattr localhost@tcp:/action /foo')

    def test_start_client_both_options(self):
        """test command line start client (both options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        client = self.fs.new_client(self.srv1, "/foo")
        action = StartClient(client, mount_options='acl', addopts='user_xattr')
        self.check_cmd(action, 'mkdir -p "/foo" && /sbin/modprobe lustre && ' +
           '/bin/mount -t lustre -o acl,user_xattr localhost@tcp:/action /foo')

    def test_stop_client_simple(self):
        """test command line stop client (simple)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        client = self.fs.new_client(self.srv1, "/foo")
        action = StopClient(client)
        self.check_cmd(action, 'umount /foo')

    def test_stop_client_addopts(self):
        """test command line stop client (addl opts)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        client = self.fs.new_client(self.srv1, "/foo")
        action = StopClient(client, addopts='-f')
        self.check_cmd(action, 'umount -f /foo')


    #
    # Target
    #

    def test_fsck(self):
        """test command line fsck"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        action = Fsck(tgt)
        self.check_cmd(action, 'e2fsck -y /dev/root')

    def test_fsck_addopts(self):
        """test command line fsck (addl options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        action = Fsck(tgt, addopts='-f')
        self.check_cmd(action, 'e2fsck -y /dev/root -f')

    # XXX: All _check_status() calls should be replaced by a real call to the
    # method dedicated action for the Target.

    def test_start_target(self):
        """test command line start target"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt)
        self.check_cmd(action,
                'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
                '/bin/mount -t lustre /dev/root /mnt/action/mgt/0')

    def test_start_target_addopts(self):
        """test command line start target (addl options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt, addopts='abort_recov')
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
               '/bin/mount -t lustre -o abort_recov /dev/root /mnt/action/mgt/0')

    def test_start_target_mount_options(self):
        """test command line start target (mount_options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt, mount_options={'mgt': 'abort_recov'})
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
               '/bin/mount -t lustre -o abort_recov /dev/root /mnt/action/mgt/0')

    def test_start_target_mount_options_none(self):
        """test command line start target (mount_options missing)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt, mount_options={'mdt': 'abort_recov'})
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
               '/bin/mount -t lustre /dev/root /mnt/action/mgt/0')

        action = StartTarget(tgt, mount_options={'mgt': None})
        self.check_cmd(action,
               'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
               '/bin/mount -t lustre /dev/root /mnt/action/mgt/0')

    def test_start_target_both_options(self):
        """test command line start target (both options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt, addopts='ro',
                             mount_options={'mgt': 'abort_recov'})
        self.check_cmd(action,
             'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
             '/bin/mount -t lustre -o abort_recov,ro /dev/root /mnt/action/mgt/0')

    def test_start_target_jdev(self):
        """test command line start target (with journal)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/hda', '/dev/hda1')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt)
        self.check_cmd(action,
          'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
          '/bin/mount -t lustre -o journal_dev=0x301 /dev/hda /mnt/action/mgt/0')

    def test_start_target_file_device(self):
        """test command line start target (file device)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/etc/passwd')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt)
        self.check_cmd(action,
                'mkdir -p "/mnt/action/mgt/0" && /sbin/modprobe lustre && ' +
                '/bin/mount -t lustre -o loop /etc/passwd /mnt/action/mgt/0')

    def test_start_target_mount_paths(self):
        """test command line start target (mount paths)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/mypath'})
        self.check_cmd(action,
                'mkdir -p "/mnt/mypath" && /sbin/modprobe lustre && ' +
                '/bin/mount -t lustre /dev/root /mnt/mypath')

    def test_start_target_custom_mount_paths(self):
        """test command line start target (custom mount paths)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        # fs_name
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$fs_name/mgt'})
        self.check_cmd(action,
                'mkdir -p "/mnt/action/mgt" && /sbin/modprobe lustre && ' +
                '/bin/mount -t lustre /dev/root /mnt/action/mgt')
        # index
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/mgt/$index'})
        self.check_cmd(action,
                'mkdir -p "/mnt/mgt/0" && /sbin/modprobe lustre && ' +
                '/bin/mount -t lustre /dev/root /mnt/mgt/0')
        # type
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$type/$index'})
        self.check_cmd(action,
                'mkdir -p "/mnt/mgt/0" && /sbin/modprobe lustre && ' +
                '/bin/mount -t lustre /dev/root /mnt/mgt/0')
        # label
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$label'})
        self.check_cmd(action, 'mkdir -p "/mnt/MGS" && /sbin/modprobe lustre' +
                               ' && /bin/mount -t lustre /dev/root /mnt/MGS')

        # Bad variable, leave it as-is
        action = StartTarget(tgt, mount_paths={'mgt': '/mnt/$bad'})
        self.check_cmd(action,
                'mkdir -p "/mnt/$bad" && /sbin/modprobe lustre && ' +
                '/bin/mount -t lustre /dev/root /mnt/$bad')

    # Stop
    def test_stop_target(self):
        """test command line stop target"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StopTarget(tgt)
        self.check_cmd(action, 'umount /dev/root')

    def test_stop_target_addopts(self):
        """test command line stop target (addl options)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = StopTarget(tgt, addopts='-l')
        self.check_cmd(action, 'umount -l /dev/root')

    def test_stop_target_file_device(self):
        """test command line stop target (file device)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/etc/passwd')
        tgt._check_status(mountdata=False)
        action = StopTarget(tgt)
        self.check_cmd(action, 'umount -d /etc/passwd')

    # Format
    def check_cmd_format(self, action, cmdline):
        """Helper method to check cmdline for format actions"""
        self.check_cmd(action,
                 'mkfs.lustre --reformat --quiet "--fsname=action" ' + cmdline)

    def test_format_target(self):
        """test command line format (MGT)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--mgs /dev/root')

    def test_format_target_loopback(self):
        """test command line format (MGT in loopback)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/etc/passwd')
        tgt._check_status(mountdata=False)
        action = Format(tgt)
        size = os.stat('/etc/passwd').st_size / 1024
        self.check_cmd_format(action, '--mgs --device-size=%d /etc/passwd' %
                size)

    def test_format_target_jdev(self):
        """test command line format (MGT with jdev and mkfsoptions)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root', '/dev/root1')
        tgt._check_status(mountdata=False)
        action = Format(tgt, mkfs_options={'mgt': '-m 2'})
        jaction = JournalFormat(tgt, action)
        self.check_cmd(jaction, 'mke2fs -q -F -O journal_dev -b 4096 /dev/root1')
        self.check_cmd_format(action, '--mgs ' +
                         '"--mkfsoptions=-j -J device=/dev/root1 -m 2" /dev/root')

    def test_format_target_mdt(self):
        """test command line format (MDT)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--mdt --index=0 ' +
                              '"--mgsnode=localhost@tcp" /dev/root')

    def test_format_target_mdt_options(self):
        """test command line format (MDT with addl options)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt, addopts='-v')
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" -v /dev/root')

    def test_format_target_mdt_quota(self):
        """test command line format (MDT with quota)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt, quota=True, quota_type='ug')
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" "--param=mdt.quota_type=ug" /dev/root')

    def test_format_target_mdt_striping(self):
        """test command line format (MDT with striping)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt, stripecount=2, stripesize=2097152)
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" --param=lov.stripecount=2 ' +
             '--param=lov.stripesize=2097152 /dev/root')

    def test_format_target_mdt_mkfsoptions(self):
        """test command line format (MDT with mkfsoptions)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt, mkfs_options={'mdt': '-m 2'})
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" "--mkfsoptions=-m 2" /dev/root')

    def test_format_target_mdt_param(self):
        """test command line format (MDT with param)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'mdt', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt, format_params={'mdt': 'foo'})
        self.check_cmd_format(action, '--mdt --index=0 ' +
             '"--mgsnode=localhost@tcp" "--param=foo" /dev/root')

    def test_format_target_ost(self):
        """test command line format (OST)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'ost', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
                              '"--mgsnode=localhost@tcp" /dev/root')

    def test_format_target_ost_quota(self):
        """test command line format (OST with quota)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv2, 'ost', 0, '/dev/root')
        tgt._check_status(mountdata=False)
        action = Format(tgt, quota=True, quota_type='ug')
        self.check_cmd_format(action, '--ost --index=0 ' +
             '"--mgsnode=localhost@tcp" "--param=ost.quota_type=ug" /dev/root')

    def test_format_target_ost_failnode(self):
        """test command line format (OST with failnode)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root')
        tgt.add_server(self.srv2)
        tgt._check_status(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
             '"--mgsnode=localhost@tcp" "--failnode=localhost2@tcp" /dev/root')

    def test_format_target_ost_two_failnodes(self):
        """test command line format (OST with 2 failnodes)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root')
        tgt.add_server(self.srv2)
        tgt.add_server(Server('localhost3', ['localhost3@tcp']))
        tgt._check_status(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
             '"--mgsnode=localhost@tcp" "--failnode=localhost2@tcp" ' +
             '"--failnode=localhost3@tcp" /dev/root')

    def test_format_target_ost_failnodes_network(self):
        """test command line format (OST with 2 failnodes and network)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        tgt = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root', network='tcp')
        tgt.add_server(self.srv2)
        tgt.add_server(Server('localhost3', ['localhost3@o2ib']))
        tgt._check_status(mountdata=False)
        action = Format(tgt)
        self.check_cmd_format(action, '--ost --index=0 ' +
          '"--mgsnode=localhost@tcp" "--failnode=localhost2@tcp" ' +
          '--network=tcp /dev/root')

    # Tunefs
    def check_cmd_tunefs(self, action, cmdline):
        """Helper method to check cmdline for tunefs actions"""
        self.check_cmd(action,
                 'tunefs.lustre --erase-params --quiet ' + cmdline)

    def test_tunefs_mgs(self):
        """test command line tunefs writeconf (MGT)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        action = Tunefs(tgt, writeconf=True)
        self.check_cmd_tunefs(action, '--writeconf /dev/root')

    def test_tunefs_mgs(self):
        """test command line tunefs addl options (MGT)"""
        tgt = self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        action = Tunefs(tgt, addopts='-v')
        self.check_cmd_tunefs(action, '-v /dev/root')

    def test_tunefs_mdt(self):
        """test command line tunefs (MDT)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, '/dev/root')
        action = Tunefs(mdt)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" /dev/root')

    def test_tunefs_ost(self):
        """test command line tunefs (OST)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root')
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" /dev/root')

    def test_tunefs_mdt_striping(self):
        """test command line tunefs striping (MDT)"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, '/dev/root')
        action = Tunefs(mdt, stripecount=2, stripesize=2097152)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '--param=lov.stripecount=2 ' +
                              '--param=lov.stripesize=2097152 /dev/root')

    def test_tunefs_target_quota(self):
        """test command line tunefs quota"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        mdt = self.fs.new_target(self.srv1, 'mdt', 0, '/dev/root')
        action = Tunefs(mdt, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=mdt.quota_type=ug" /dev/root')
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/sdb')
        action = Tunefs(ost, quota=True, quota_type='ug')
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=ost.quota_type=ug" /dev/sdb')

    def test_tunefs_target_failnode(self):
        """test command line tunefs failnode"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root')
        ost.add_server(self.srv2)
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--failnode=localhost2@tcp" /dev/root')

    def test_tunefs_target_network(self):
        """test command line tunefs network"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root', network='tcp')
        ost.add_server(self.srv2)
        ost.add_server(Server('localhost3', ['localhost3@o2ib']))
        action = Tunefs(ost)
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                           '"--failnode=localhost2@tcp" --network=tcp /dev/root')

    def test_tunefs_target_format_params(self):
        """test command line tunefs format params"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root')
        action = Tunefs(ost, format_params={'ost': 'foo'})
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--param=foo" /dev/root')

    def test_tunefs_target_mkfsoptions(self):
        """test command line tunefs mkfsoptions"""
        self.fs.new_target(self.srv1, 'mgt', 0, '/dev/root')
        ost = self.fs.new_target(self.srv1, 'ost', 0, '/dev/root')
        action = Tunefs(ost, mkfs_options={'ost': '-m 2'})
        self.check_cmd_tunefs(action, '"--mgsnode=localhost@tcp" ' +
                              '"--mkfsoptions=-m 2" /dev/root')
