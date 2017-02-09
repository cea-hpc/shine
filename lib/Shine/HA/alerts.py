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
shine-HA alerts module
"""

import logging
from operator import attrgetter
import sys

LOGGER = logging.getLogger(__name__)


ALERT_CLS_FS = 0
ALERT_CLS_LNET = 1
ALERT_CLS_HA = 2


class Alert(object):
    """Base Alert class"""

    def __init__(self, name, sortkey=0):
        self.name = name
        # sortkey integer may be used to sort Alerts
        # 1000 is reserved by HACore which should be last
        self.sortkey = sortkey
        self.levels = set()

    def info(self, aclass, message, ctx=None):
        raise NotImplementedError

    def warning(self, aclass, message, ctx=None):
        raise NotImplementedError

    def critical(self, aclass, message, ctx=None):
        raise NotImplementedError


class AlertManager(object):
    """Class that manages shine-HA alerts.

    Three alert levels are supported by this class:
        - INFO
        - WARNING
        - CRITICAL

    Email or custom alerts can be triggered at each level.
    """
    def __init__(self):
        self.alerts = {}
        self.hacore = None
        self.lnetmon = None
        self.reply_port = None

    @classmethod
    def fromcfg(cls, config_dic):
        """Convenient constructor that supports shine-HA config dict"""
        inst = AlertManager()

        # Load defined Alert plugins
        if 'alert_plugins' in config_dic:
            alert_plugins = config_dic['alert_plugins']
            for name, plugin_cfg in alert_plugins.iteritems():
                LOGGER.debug('Found Alert plugin %s in config: %s', name,
                             plugin_cfg)
                try:
                    mod = __import__(plugin_cfg['module'], fromlist=[None])
                    LOGGER.debug('Loaded %s', mod)
                    inst.define_alert(mod.ALERT_CLASS(**plugin_cfg.get('args')))
                except ImportError as exc:
                    LOGGER.error(exc)
                    sys.exit(1)

        # Enable alerts
        if 'alerts' in config_dic:
            alerts = config_dic['alerts']
            for level, level_name in enumerate(('INFO', 'WARN', 'CRIT')):
                for alert_name in alerts.get(level_name, []):
                    inst.enable_alert(alert_name, level)

        # Enable HA if needed
        if 'HA' in config_dic:
            from Shine.HA.hacore import HACore

            hacfg = config_dic['HA']
            inst.hacore = HACore(inst, **hacfg)
            inst.define_alert(inst.hacore)
            inst.enable_alert(inst.hacore.name, 0)
            inst.enable_alert(inst.hacore.name, 2)
        return inst

    def define_alert(self, alert):
        LOGGER.debug('AlertManager: adding %s alert definition', alert.name)
        self.alerts[alert.name] = alert

    def enable_alert(self, alert_name, level):
        LEVELS = ['INFO', 'WARN', 'CRIT']
        LOGGER.info('Enabling alert level %s for %s', LEVELS[level], alert_name)
        self.alerts[alert_name].levels.add(level)

    def info(self, aclass, message, ctx=None):
        """Trigger an informative alert"""
        for alert in sorted(self.alerts.values(), key=attrgetter('sortkey')):
            if 0 in alert.levels:
                LOGGER.debug('Triggering Alert %s (INFO)', alert.name)
                alert.info(aclass, message, ctx)

    def warning(self, aclass, message, ctx=None):
        """Trigger a warning alert"""
        for alert in sorted(self.alerts.values(), key=attrgetter('sortkey')):
            if 1 in alert.levels:
                LOGGER.debug('Triggering Alert %s (WARNING)', alert.name)
                alert.warning(aclass, message, ctx)

    def critical(self, aclass, message, ctx=None):
        """Trigger a critical alert"""
        for alert in sorted(self.alerts.values(), key=attrgetter('sortkey')):
            if 2 in alert.levels:
                LOGGER.debug('Triggering Alert %s (CRITICAL)', alert.name)
                alert.critical(aclass, message, ctx)
