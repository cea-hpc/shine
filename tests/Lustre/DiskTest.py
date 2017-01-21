#!/usr/bin/env python
# Shine.Lustre.Disk test suite
# Written by A. Degremont 2009-08-03


"""Unit test for Shine.Lustre.Disk"""

import unittest
from subprocess import Popen, PIPE, STDOUT

import Utils
from Shine.Lustre.Disk import Disk, DiskDeviceError, DiskNoDeviceError

class DiskLoopbackTest(unittest.TestCase):

    def format(self, *opts):
        cmd = []
        cmd += ["/usr/sbin/mkfs.lustre", "--device-size", str(self.size / 1024)]
        cmd += opts
        cmd.append(self.dev)
        process = Popen(cmd, stdout=PIPE, stderr=STDOUT)
        process.wait()
        self.assertEqual(process.returncode, 0)

    def setUp(self):
        self.size = 450 * 1024 * 1024
        self.diskfile = Utils.make_disk(450)
        self.dev = self.diskfile.name
        self.disk = Disk(dev=self.dev)

    def testLoopbackDevCheck(self):
        """test device check with a loopback device"""
        self.disk._device_check()
        self.assertEqual(self.disk.dev_isblk, False)
        self.assertEqual(self.disk.dev_size, self.size)

    @Utils.rootonly
    def testMountDataFlags(self):
        """test mountdata flag check when freshly formatted"""

        self.format("--fsname=nonreg", "--ost", "--mgsnode=127.0.0.1@lo")

        self.disk._mountdata_check()

        # first_time TRUE
        self.assertTrue(self.disk.has_first_time_flag())
        # need_index TRUE
        self.assertTrue(self.disk.has_need_index_flag())
        # update TRUE
        self.assertTrue(self.disk.has_update_flag())
        # rewrite_ldd FALSE
        self.assertFalse(self.disk.has_rewrite_ldd_flag())
        # writeconf FALSE
        self.assertFalse(self.disk.has_writeconf_flag())
        # upgrade14 FALSE
        self.assertFalse(self.disk.has_upgrade14_flag())
        # param FALSE
        self.assertFalse(self.disk.has_param_flag())

        self.assertEqual(self.disk.flags(),
                         ['need_index', 'first_time', 'update'])

    @Utils.rootonly
    def test_mountdata_label_mgs(self):
        """test mountdata check with fsname and MGS as label"""

        self.format("--fsname=nonreg", "--mgs", "--param", "sys.timeout=40")

        self.disk._mountdata_check(label_check="MGS")

        # update TRUE
        self.assertTrue(self.disk.has_update_flag())
        # rewrite_ldd FALSE
        self.assertFalse(self.disk.has_rewrite_ldd_flag())
        # writeconf FALSE
        self.assertFalse(self.disk.has_writeconf_flag())
        # upgrade14 FALSE
        self.assertFalse(self.disk.has_upgrade14_flag())
        # param FALSE
        self.assertFalse(self.disk.has_param_flag())

        # Starting from Lustre 2.4, 'need_index' and 'first_time' flags are no
        # more set
        flags = self.disk.flags()
        if 'need_index' in flags:
            flags.remove('need_index')
        if 'first_time' in flags:
            flags.remove('first_time')
        self.assertEqual(flags, ['update'])

    @Utils.rootonly
    def test_mountdata_label_ost(self):
        """test mountdata check with fsname and label for an OST"""

        self.format("--fsname=nonreg", "--ost", "--mgsnode=127.0.0.1@lo",
                    "--param", "sys.timeout=40")

        self.disk._mountdata_check(label_check="nonreg-OSTffff")

        # first_time TRUE
        self.assertTrue(self.disk.has_first_time_flag())
        # need_index TRUE
        self.assertTrue(self.disk.has_need_index_flag())
        # update TRUE
        self.assertTrue(self.disk.has_update_flag())
        # rewrite_ldd FALSE
        self.assertFalse(self.disk.has_rewrite_ldd_flag())
        # writeconf FALSE
        self.assertFalse(self.disk.has_writeconf_flag())
        # upgrade14 FALSE
        self.assertFalse(self.disk.has_upgrade14_flag())
        # param FALSE
        self.assertFalse(self.disk.has_param_flag())

        self.assertEqual(self.disk.flags(),
                         ['need_index', 'first_time', 'update'])

    @Utils.rootonly
    def testMountDataBadLabel(self):
        """test mountdata check with wrong fsname and label"""
        self.format("--fsname=nonreg","--mgs")
        self.assertRaises(DiskDeviceError, self.disk._mountdata_check,
                          label_check="MDT")
        self.assertRaises(DiskDeviceError, self.disk._mountdata_check,
                          label_check="bad_label")

    def testMountDataNoFormat(self):
        """test mountdata on a not formatted device"""
        self.assertRaises(DiskDeviceError, self.disk._mountdata_check)


class DiskOtherTest(unittest.TestCase):

    def testErrorDevCheck(self):
        """test device check with a wrong device"""
        disk = Disk(dev='wrong path')
        self.assertRaises(DiskNoDeviceError, disk._device_check)

    def testBadDevCheck(self):
        """test device check with a bad file"""
        disk = Disk(dev='/dev/tty0')
        self.assertRaises(DiskDeviceError, disk._device_check)

    ### XXX: This does not check the device size
    def testBlockDevCheck(self):
        """test device check with a block device"""
        disk = Disk(Utils.get_block_dev())
        disk._device_check()
        self.assertEqual(disk.dev_isblk, True)
        self.assertNotEqual(disk.dev_size, 0)

    def testUpdate(self):
        """test update a Disk instance with another one"""
        disk1 = Disk(dev='a_dev')
        disk1.dev_size = 1234
        disk2 = Disk(dev='b_dev')
        disk2.dev_size = 5678
        disk1.update(disk2)

        self.assertEqual(disk1.dev_size, disk2.dev_size)

    def testException(self):
        """test Disk exception classes"""
        disk = Disk(dev="foo")
        exp = DiskDeviceError(disk=disk, message="Something")
        self.assertEqual(str(exp), "Something")
