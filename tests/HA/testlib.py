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


"""HA test helper library"""

import logging
import tempfile
import time
import unittest

from ClusterShell.NodeSet import NodeSet
from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.FileSystem import FileSystem as FSConfig
from Shine.Lustre.FileSystem import FileSystem
import Shine.FSUtils as FSUtils

from Shine.HA.alerts import Alert

LOGGER = logging.getLogger(__name__)

# G_XMF is set by ShineHAScenarioConfig as an hack used to pass custom XMF
# content to open_test_lustrefs()
G_XMF = None


def make_temp_file(text, suffix='', indir=None):
    """Create a temporary file with the provided text."""
    tmp = tempfile.NamedTemporaryFile(prefix='shine-ha-test-',
                                      suffix=suffix, dir=indir)
    tmp.write(text)
    tmp.flush()
    return tmp


#
# open_lustrefs() override
#
# create a temporary xmf file with testlib.xmf content and then open FS
#
def open_test_lustrefs(fs_name, target_types=None, nodes=None, excluded=None,
                       failover=None, indexes=None, labels=None, groups=None,
                       event_handler=None, extended=False):

    # Create file system configuration
    tmpfile = make_temp_file(G_XMF)
    fs_conf = Configuration()
    fs_conf._fs = FSConfig(tmpfile.name)
    fs_conf.xmf_path = tmpfile.name
    LOGGER.debug('open_test_lustrefs: using %s', fs_conf.xmf_path)

    fs = FSUtils.instantiate_lustrefs(fs_conf, target_types, nodes, excluded,
                                      failover, indexes, labels, groups,
                                      event_handler, extended=extended)

    return fs_conf, fs


class ShineHAScenarioConfig(object):
    """Configure shine-HA test scenario"""

    def __init__(self, xmf):
        global G_XMF
        G_XMF = xmf
        self.evolution = []
        self.epoch = time.time()
        self.comp_states = {}

    def add_states(self, ts, states):
        self.evolution.append((ts, states))
        self.evolution.sort()
        LOGGER.debug('evolution %s', self.evolution)

    def update_fs_components(self, fs, fs_components):
        now = time.time()

        next_ts, states = self.evolution[0]
        LOGGER.debug('(now - epoch)=%d next_ts=%d', now - self.epoch, next_ts)
        if now - self.epoch >= next_ts:
            if states is None:
                LOGGER.debug('test complete')
                fs.TEST_COMPLETED = True
                return
            next_ts, self.comp_states = self.evolution.pop(0)
            LOGGER.debug('set new component states (ts=%d)', next_ts)

        for comp in fs_components:
            if type(self.comp_states[comp.uniqueid()]) is tuple:
                # migrated
                comp_state, server = self.comp_states[comp.uniqueid()]
                failover_node = NodeSet(server)
                comp.failover(failover_node)
                comp.state = comp_state
                assert comp.defaultserver == failover_node
                LOGGER.debug('set compoment %s FAILOVER state %s on %s',
                             comp.uniqueid(), comp.state, comp.defaultserver)
            else:
                comp.state = self.comp_states[comp.uniqueid()]

                LOGGER.debug('set compoment %s state %s on %s', comp.uniqueid(),
                             comp.state, comp.defaultserver)
            assert comp.state is not None


class FileSystemMock(FileSystem):
    """Lustre.FileSystem Mock class"""

    SCENARIO = None

    def status(self, comps=None, **kwargs):
        LOGGER.debug('FileSystemMock.status fs_name=%s', self.fs_name)
        comps = (comps or self.components).managed(supports='status')
        self.SCENARIO.update_fs_components(self, comps)


class TestAlert(Alert):
    """A test Alert object that tracks what's going on"""

    def __init__(self, name):
        Alert.__init__(self, name)
        self.info_alerts = []
        self.warn_alerts = []
        self.crit_alerts = []

    def info(self, aclass, message, ctx=None):
        self.info_alerts.append((aclass, message, ctx))

    def warning(self, aclass, message, ctx=None):
        self.warn_alerts.append((aclass, message, ctx))

    def critical(self, aclass, message, ctx=None):
        self.crit_alerts.append((aclass, message, ctx))
