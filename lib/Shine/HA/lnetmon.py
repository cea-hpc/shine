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


"""
shine-HA Lustre Network monitoring module
"""

import logging

from ClusterShell.Event import EventHandler
from Shine.HA.alerts import ALERT_CLS_LNET


DEFAULT_LNET_COMMAND = 'lctl ping %s'
DEFAULT_LNET_CMD_TIMEOUT = 10
DEFAULT_LNET_ALERT_THRESHOLDS = [1, 1, 2]

LOGGER = logging.getLogger(__name__)

NID_STATE_UP = 0
NID_STATE_ERROR = 1
NID_STATE_TIMEOUT = 2

NID_STATE_STRINGS = ['UP', 'ERROR', 'TIMEOUT']


class NodeNidsState(object):
    """Node NIDs state class"""

    def __init__(self, node):
        self.node = node
        self._states = {}
        self.down_count = 0

    def __iter__(self):
        return self._states.iterkeys()

    def __len__(self):
        return len(self._states)

    def nids(self):
        return self._states.keys()

    def set_nids(self, nids):
        for nid in nids:
            self._states.setdefault(nid, 0)

    def get_state(self):
        # At least one NID_STATE_UP is enough to consider the node as alive
        return min(self._states.values())

    def set_nid_state(self, nid, state):
        LOGGER.debug('NodeNidsState: setting state %s for nid %s of node %s',
                     NID_STATE_STRINGS[state], nid, self.node)
        self._states[nid] = state


class LNetPingerHandler(EventHandler):
    """
    LNet Pinger Event Handler
    """
    def __init__(self, lnetmon, nidss, nid):
        EventHandler.__init__(self)
        self.lnetmon = lnetmon      # LNetMonitor
        self.nidss = nidss          # NidsState object
        self.nid = nid

    def ev_error(self, worker):
        LOGGER.debug('LNetPingerHandler[%s:%s](stderr): %s', self.nidss.node,
                     self.nid, worker.current_errmsg)

    def ev_close(self, worker):
        if worker.did_timeout():
            state = NID_STATE_TIMEOUT
        elif worker.current_rc == 0:
            state = NID_STATE_UP
        else:
            state = NID_STATE_ERROR
        self.nidss.set_nid_state(self.nid, state)
        self.lnetmon.check_errors()


class LNetMonitor(EventHandler):
    """
    LNetMonitor class that performs ping checks on known filesystem nids.
    """

    def __init__(self, task, fs_name, alert_mgr, lnet_args):
        EventHandler.__init__(self)
        self.task = task
        self.fs_name = fs_name
        self.alert_mgr = alert_mgr

        # lnet_args
        self.alert_thresholds = lnet_args.get('failure_count_thresholds',
                                              DEFAULT_LNET_ALERT_THRESHOLDS)
        self.command = lnet_args.get('command', DEFAULT_LNET_COMMAND)
        self.command_timeout = lnet_args.get('command_timeout',
                                             DEFAULT_LNET_CMD_TIMEOUT)

        self.fs_conf = None

        # node nids state: node -> NodeNidsState
        self.nnidss = {}
        self.checkerr_timer = None

        # Global optimal state
        self.state_optimal = True

    def ping(self):
        if not self.fs_conf:
            LOGGER.debug('LNetMonitor.ping: fs_conf not set')
            return

        for target in self.fs_conf.iter_targets():
            node = target.get_nodename()
            nids = self.fs_conf.get_nid(node)
            self.nnidss.setdefault(node, NodeNidsState(node)).set_nids(nids)

        cnt = 0
        for node, nidss in self.nnidss.items():
            cnt += len(nidss)
            for nid in nidss:
                command = self.command % nid
                LOGGER.debug('Executing: %s', command)
                pinger_handler = LNetPingerHandler(self, nidss, nid)
                worker = self.task.shell(command, stderr=True,
                                         timeout=self.command_timeout,
                                         handler=pinger_handler)
                worker.set_write_eof() # see CS #333

        LOGGER.debug('LNetMonitor.ping: checking %d nids on %d nodes', cnt,
                     len(self.nnidss))

    def check_errors(self):
        if self.checkerr_timer and self.checkerr_timer.is_valid():
            # postpone timer a little bit
            self.checkerr_timer.set_nextfire(1)
        else:
            # schedule a new timer in 1 sec
            self.checkerr_timer = self.task.timer(1, handler=self)

    def nodes_down(self):
        return ((nidss.node, nidss) for nidss in self.nnidss.values()
                if nidss.get_state() != NID_STATE_UP)

    def ev_timer(self, timer):
        timer.invalidate()

        optimal = True
        down_cnt_mtx = [[], [], []] # info,warn,crit

        for node, nidss in self.nodes_down():
            LOGGER.debug('LNetMonitor: node %s is down (down_count=%d)', node,
                         nidss.down_count)

            optimal = False
            nidss.down_count += 1

            for level in reversed(range(3)):
                if nidss.down_count == self.alert_thresholds[level]:
                    down_cnt_mtx[level].append(nidss)
                    break

        if optimal:
            # No errors
            if not self.state_optimal:
                msg = 'All LNet NIDs are UP'
                ctx = {'FSMonitor': self}
                self.alert_mgr.info(ALERT_CLS_LNET, msg, ctx)
                self.state_optimal = True
            return

        self.state_optimal = False

        for level, level_name in enumerate(('info', 'warning', 'critical')):

            if not down_cnt_mtx[level]:
                continue

            msg = 'LNet ping failed (%s)' % level_name
            LOGGER.warning('[%s] %s', level_name, msg)

            ctx = {'LNetMonitor': self,
                   'nodelist': list(nidss.node
                                    for nidss in down_cnt_mtx[level]),
                   'down_cnt_list': down_cnt_mtx[level]}

            getattr(self.alert_mgr, level_name)(ALERT_CLS_LNET, msg, ctx)
