#!/usr/bin/env python
# Shine.Lustre.Disk test suite
# Written by A. Degremont 2009-08-03
# $Id$


"""Unit test for Shine.Lustre.Disk"""

import sys
import unittest
import tempfile
from subprocess import *

sys.path.insert(0, '../lib')

from Shine.Lustre.Disk import *

class ServerLoopbackTest(unittest.TestCase):

    def makeFileDevice(self, size):
        # Get a temporary name for a file
        fd, filename = tempfile.mkstemp(prefix="shine-nonreg-",suffix=".dev")
        os.lseek(fd, size - 1, 0)
        os.write(fd, 'A')
        os.close(fd)
        return filename

    def format(self, *opts):
        cmd = []
        cmd += ["/usr/sbin/mkfs.lustre","--device-size", str(self.size / 1024)]
        cmd += opts
        cmd.append(self.dev)
        p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
        p.wait()
        self.assertEqual(p.returncode, 0)

    def setUp(self):
        self.size = 450 * 1024 * 1024
        self.jsize = 450 * 1024 * 1024
        self.dev = self.makeFileDevice(self.size)
        self.jdev = self.makeFileDevice(self.jsize)

    def tearDown(self):
        os.unlink(self.dev)
        os.unlink(self.jdev)

    def testLoopbackDevCheck(self):
        """test device check with a loopback device"""
        d = Disk(dev=self.dev)
        d._device_check()
        self.assertEqual(d.dev_isblk, False)
        self.assertEqual(d.dev_size, self.size)

    def testMountDataFlags(self):
        """test mountdata flag check when freshly formatted"""

        self.format("--fsname=nonreg","--mgs")

        d = Disk(dev=self.dev)
        d._disk_check()

        # first_time TRUE
        self.assertTrue(d.has_first_time_flag())
        # need_index TRUE
        self.assertTrue(d.has_need_index_flag())
        # update TRUE
        self.assertTrue(d.has_update_flag())
        # rewrite_ldd FALSE
        self.assertFalse(d.has_rewrite_ldd_flag())
        # writeconf FALSE
        self.assertFalse(d.has_writeconf_flag())
        # upgrade14 FALSE
        self.assertFalse(d.has_upgrade14_flag())
        # param FALSE
        self.assertFalse(d.has_param_flag())

    def testMountDataLabel(self):
        """test mountdata check with fsname and MGS as label"""

        self.format("--fsname=nonreg","--mgs","--param","sys.timeout=40")

        d = Disk(dev=self.dev)
        d._disk_check(fsname_check="nonreg", label_check="MGS")

        # first_time TRUE
        self.assertTrue(d.has_first_time_flag())
        # need_index TRUE
        self.assertTrue(d.has_need_index_flag())
        # update TRUE
        self.assertTrue(d.has_update_flag())
        # rewrite_ldd FALSE
        self.assertFalse(d.has_rewrite_ldd_flag())
        # writeconf FALSE
        self.assertFalse(d.has_writeconf_flag())
        # upgrade14 FALSE
        self.assertFalse(d.has_upgrade14_flag())
        # param FALSE
        self.assertFalse(d.has_param_flag())
        # ldd_param
        self.assertEqual(d._ldd_params, "sys.timeout=40")

    def testMountDataBadLabel(self):
        """test mountdata check with wrong fsname and label"""

        self.format("--fsname=nonreg","--mgs")

        d = Disk(dev=self.dev)
        self.assertRaises(DiskDeviceError, d._disk_check,fsname_check="something_else", label_check="MGS")
        self.assertRaises(DiskDeviceError, d._disk_check,fsname_check="nonreg", label_check="MDT")
        self.assertRaises(DiskDeviceError, d._disk_check,fsname_check="bad_fsname", label_check="bad_label")

    def testMountDataNoFormat(self):
        """test mountdata on a not formatted device"""

        d = Disk(dev=self.dev)
        self.assertRaises(DiskDeviceError, d._disk_check)


class ServerOtherTest(unittest.TestCase):

    def testErrorDevCheck(self):
        """test device check with a wrong device"""
        d = Disk(dev='wrong path')
        self.assertRaises(DiskDeviceError, d._device_check)

    def testBadDevCheck(self):
        """test device check with a bad file"""
        d = Disk(dev='/dev/tty0')
        self.assertRaises(DiskDeviceError, d._device_check)

    ### XXX: /dev/sda is hardcoded
    ### XXX: This does not check the device size
    def testBlockDevCheck(self):
        """test device check with a block device"""
        d = Disk(dev='/dev/sda')
        d._device_check()
        self.assertEqual(d.dev_isblk, True)
        self.assertNotEqual(d.dev_size, 0)

    def testUpdate(self):
        """test update a Disk instance with another one"""

        d1 = Disk(dev='a_dev', jdev='a_jdev')
        d1.dev_size = 1234
        d1.ldd_fsname = "fsname"
        d2 = Disk(dev='b_dev', jdev='b_jdev')
        d2.dev_size = 5678
        d2.ldd_fsname = "other"
        d1.update(d2)

        self.assertEqual(d1.dev_size, d2.dev_size)
        self.assertEqual(d1.ldd_fsname, d2.ldd_fsname)

    def testException(self):
        """test Disk exception classes"""
        d = Disk(dev="foo")

        e = DiskException(disk=d)

        e = DiskDeviceError(disk=d, message="Something")
        self.assertEqual(str(e), "Something")


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ServerLoopbackTest)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(ServerOtherTest))
    unittest.TextTestRunner(verbosity=2).run(suite)
