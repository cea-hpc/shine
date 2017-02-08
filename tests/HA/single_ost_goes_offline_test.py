#!/usr/bin/python
#
# Copyright (C) 2017 Board of Trustees, Leland Stanford Jr. University
#
# Written by Stephane Thiell <sthiell@stanford.edu>
#
#   --*-*- Stanford University Research Computing Center -*-*--
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Unit test for Shine.HA"""

import logging
from textwrap import dedent
import unittest

import Shine.FSUtils as FSUtils
from Shine.Lustre.Component import OFFLINE, MOUNTED
from Shine.HA.main import start, LOGGING_FORMAT, DEFAULT_COMP_ALERT_THRESHOLDS
from Shine.HA.alerts import AlertManager, ALERT_CLS_FS

# HA testlib
import testlib


LOGGER = logging.getLogger(__name__)


class ShineHATest(unittest.TestCase):
    """Shine HA Test Case"""

    # Shine test filesystem configuration
    XMF = dedent("""
         mdt:node=testfs-md1-s2 index=0 dev=/dev/mapper/md1-rbod1-mdt0 ha_node=testfs-md1-s1
         ost:node=testfs-io1-s1 index=0 dev=/dev/md0 ha_node=testfs-io1-s2
         ost:node=testfs-io1-s2 index=1 dev=/dev/md1 ha_node=testfs-io1-s1
         ost:node=testfs-io1-s1 index=2 dev=/dev/md2 ha_node=testfs-io1-s2
         ost:node=testfs-io1-s2 index=3 dev=/dev/md3 ha_node=testfs-io1-s1
         ost:node=testfs-io1-s1 index=4 dev=/dev/md4 ha_node=testfs-io1-s2
         ost:node=testfs-io1-s2 index=5 dev=/dev/md5 ha_node=testfs-io1-s1
         mgt:node=testfs-md1-s1 index=0 dev=/dev/mapper/md1-rbod1-mgt ha_node=testfs-md1-s2
         fs_name:testfs
         mount_path:/test
         nid_map:nids=10.0.2.[51-52]@o2ib5 nodes=testfs-md1-s[1-2]
         nid_map:nids=10.0.2.[101-102]@o2ib5 nodes=testfs-io1-s[1-2]
         nid_map:nids=10.0.2.3@o2ib5 nodes=testfs-rbh01
         nid_map:nids=10.0.2.[220-225]@o2ib5 nodes=testfs-gw[01-06]
         """)

    def test_single_ost_goes_offline(self):

        # Setup test scenario
        scenario = testlib.ShineHAScenarioConfig(self.XMF)

        # Add as many (timestamp, new component states) as needed...
        scenario.add_states(ts=0, states={'MGS': MOUNTED,
                                          'testfs-MDT0000': MOUNTED,
                                          'testfs-OST0000': MOUNTED,
                                          'testfs-OST0001': MOUNTED,
                                          'testfs-OST0002': MOUNTED,
                                          'testfs-OST0003': MOUNTED,
                                          'testfs-OST0004': MOUNTED,
                                          'testfs-OST0005': MOUNTED})

        scenario.add_states(ts=4, states={'MGS': MOUNTED,
                                          'testfs-MDT0000': MOUNTED,
                                          'testfs-OST0000': MOUNTED,
                                          'testfs-OST0001': OFFLINE,
                                          'testfs-OST0002': MOUNTED,
                                          'testfs-OST0003': MOUNTED,
                                          'testfs-OST0004': MOUNTED,
                                          'testfs-OST0005': MOUNTED})

        # Mark the time of end of test
        scenario.add_states(ts=14, states=None)

        # Install Mocks
        FSUtils.FileSystem = testlib.FileSystemMock
        FSUtils.FileSystem.SCENARIO = scenario
        FSUtils.open_lustrefs = testlib.open_test_lustrefs

        # Enable logging
        logging.basicConfig(level=logging.DEBUG, format=LOGGING_FORMAT)

        # Install our "test" AlertManager with a single TestAlert
        alert_mgr = AlertManager()
        test_alert = testlib.TestAlert('test_alert')
        alert_mgr.define_alert(test_alert)
        alert_mgr.enable_alert('test_alert', 0)
        alert_mgr.enable_alert('test_alert', 1)
        alert_mgr.enable_alert('test_alert', 2)

        lnet_args = {'command': 'echo %s'}
        #
        # Start shine-HA engine with default alert thresholds
        #
        start(fs_name='testfs', polling_interval=1, alert_mgr=alert_mgr,
              comp_alert_thresolds=DEFAULT_COMP_ALERT_THRESHOLDS,
              lnet_args=lnet_args)

        # Test completed - check TestAlert state
        self.assertEqual(len(test_alert.info_alerts), 1)
        self.assertEqual(len(test_alert.warn_alerts), 1)
        self.assertEqual(len(test_alert.crit_alerts), 1)

        self.assertEqual(test_alert.info_alerts[0][0], ALERT_CLS_FS)
        self.assertEqual(test_alert.warn_alerts[0][0], ALERT_CLS_FS)
        self.assertEqual(test_alert.crit_alerts[0][0], ALERT_CLS_FS)
