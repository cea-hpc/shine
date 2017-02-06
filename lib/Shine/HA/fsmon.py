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
shine-HA Lustre Filesystem monitoring module
"""

import logging
import sys
import time

from Shine.Lustre.Component import MIGRATED, MOUNTED, CLIENT_ERROR, \
                                   TARGET_ERROR, RUNTIME_ERROR, OFFLINE, \
                                   NO_DEVICE, RECOVERING

from Shine.HA.alerts import ALERT_CLS_FS


STATE_TXTID_MAP = {'OFFLINE': OFFLINE, 'NO_DEVICE': NO_DEVICE,
                   'TARGET_ERROR': TARGET_ERROR, 'RUNTIME_ERROR': RUNTIME_ERROR,
                   'RECOVERING': RECOVERING, 'CLIENT_ERROR': CLIENT_ERROR}
STATE_IDTXT_MAP = {v: k for k, v in STATE_TXTID_MAP.iteritems()}

LOGGER = logging.getLogger(__name__)


class FSComponentStateCounter(object):
    """
    Helper class to keep track of a FS component state count.
    """
    def __init__(self, comp):
        self.comp = comp
        self.state = comp.state
        self.state_cnt = 1
        self.alerted_level = None

        # Keep track of the time of the first occurrence for this state
        self.started = time.time()

    def update(self, comp):
        LOGGER.debug('FSComponentAlertTracker.update %s', comp.uniqueid())
        assert self.comp.uniqueid() == comp.uniqueid()
        if self.state != comp.state:
            LOGGER.info('state changed [%s] prev=%d state_cnt=%d curr=%d(%s)',
                        comp.label, self.state, self.state_cnt,
                        comp.state, comp.text_status())
            self.state = comp.state
            self.state_cnt = 1
            self.alerted_level = None
        else:
            self.state_cnt += 1


class FSMonitor(object):
    """
    A FSMonitor object receives filesystem status updates and generates alerts
    according predefined state occurrence thresholds.
    """

    def __init__(self, task, fs_name, alert_mgr, comp_alert_thresholds):
        self.task = task
        self.fs_name = fs_name
        self.alert_mgr = alert_mgr
        # This is used to set the max number of acceptable occurrences of a
        # component in the same state (by state).
        self.comp_alert_thresholds = comp_alert_thresholds

        # Global optimal state
        self.state_optimal = True

        # track fs component history
        self.comp_state_cnt_dic = {}
        self.firsttime = True

        # last Shine FS object
        self._last_fs = None

    def _component_offline(self, comp):
        compid = comp.uniqueid()
        LOGGER.debug('_component_offline %s (%d)', compid,
                     len(self.comp_state_cnt_dic))
        if compid in self.comp_state_cnt_dic:
            self.comp_state_cnt_dic[compid].update(comp)
        else:
            self.comp_state_cnt_dic[compid] = FSComponentStateCounter(comp)

    def _component_online(self, comp):
        """A component is online; untrack if needed"""
        compid = comp.uniqueid()
        if compid in self.comp_state_cnt_dic:
            LOGGER.debug('_component_online %s (%d)', compid,
                         len(self.comp_state_cnt_dic))
            del self.comp_state_cnt_dic[compid]

            if len(self.comp_state_cnt_dic) == 0:
                msg = 'Lustre changes detected: all components of %s are ' \
                      'online' % self.fs_name
                LOGGER.info(msg)
                if True: #not self.state_optimal:
                    ctx = {'FSMonitor': self,
                           'FileSystem': self._last_fs}
                    self.alert_mgr.info(ALERT_CLS_FS, msg, ctx)
                    self.state_optimal = True

    def set_fs(self, fs_conf, fs):
        assert self.fs_name == fs.fs_name

        #
        # Check initial states: only start if all components are MOUNTED
        #
        comps = fs.components.managed(inactive=True)

        not_mounted_cnt = 0
        for comp in comps:
            # Log initial states
            LOGGER.info('Initial state for %s is %s (%s)', comp.uniqueid(),
                        comp.state, comp.text_status())
            if comp.state not in (MIGRATED, MOUNTED):
                not_mounted_cnt += 1
        if not_mounted_cnt > 0:
            LOGGER.error('Cannot run in current state: %d targets not mounted',
                         not_mounted_cnt)
            sys.exit(1)
        else:
            LOGGER.info('All %s components (%d) are online: starting HA',
                        fs.fs_name, len(comps))

    def update(self, fs_conf, fs):
        """
        Update FSMonitor object with new fs_conf and fs shine objects.

        This might trigger configured alerts.
        """

        self._last_fs = fs

        if self.firsttime:
            self.set_fs(fs_conf, fs)
            self.firsttime = False
            return

        comps = fs.components.managed(inactive=True)

        # Update component state count
        for comp in comps:
            LOGGER.debug('State for %s is %s (%s)', comp.uniqueid(),
                         comp.state, comp.text_status())

            assert comp.state is not None
            if comp.state in (MIGRATED, MOUNTED):
                self._component_online(comp)
            else:
                self._component_offline(comp)

        # Check for errors...
        comp_st_cnt_mtx = [[], [], []] # info,warn,crit

        for compid, st_cnt_obj in self.comp_state_cnt_dic.items():
            state_cnt = st_cnt_obj.state_cnt
            last_state_id = STATE_IDTXT_MAP[st_cnt_obj.state]
            thresholds = self.comp_alert_thresholds[last_state_id]

            LOGGER.debug('%s state_cnt=%d max=%d,%d,%d', compid, state_cnt,
                         *thresholds)

            # Class components based on state_cnt that reached the thresholds
            # (no alerted_level is performed here to included all components)
            for level in reversed(range(3)):
                if state_cnt >= thresholds[level]:
                    comp_st_cnt_mtx[level].append(st_cnt_obj)
                    break

        for level, level_name in enumerate(('info', 'warning', 'critical')):

            if all((scobj.alerted_level == level)
                   for scobj in comp_st_cnt_mtx[level]):

                LOGGER.debug('FSMonitor.update: no new alert level %d (%s)',
                             level, level_name)
                continue

            for scobj in comp_st_cnt_mtx[level]:
                scobj.alerted_level = level

            self.state_optimal = False

            msg = 'Some Lustre components are not available on %s' \
                  % self.fs_name
            LOGGER.warning('[%s] %s', level_name, msg)

            ctx = {'FSMonitor': self,
                   'FileSystem': self._last_fs,
                   'comp_st_cnt_list': comp_st_cnt_mtx[level]}

            # Call the proper level AlertManager method
            getattr(self.alert_mgr, level_name)(ALERT_CLS_FS, msg, ctx)
