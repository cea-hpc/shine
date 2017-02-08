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


"""
shine-HA main module

Lustre Advanced Monitoring and Standalone High Availability
"""

import argparse
import logging
import pprint
import yaml
import sys

from ClusterShell.Event import EventHandler
from ClusterShell.Task import task_self, task_terminate

from Shine.HA.alerts import AlertManager
from Shine.HA.fsactions import StatusThread
from Shine.HA.fsmon import FSMonitor
from Shine.HA.lnetmon import LNetMonitor


DEFAULT_POLLING_INTERVAL = '60'
DEFAULT_COMP_ALERT_THRESHOLDS = {'NO_DEVICE': [2, 5, 10],
                                 'OFFLINE': [2, 5, 10],
                                 'TARGET_ERROR': [5, 10, 20],
                                 'RECOVERING': [1, 10, 30]}

LOGGER = logging.getLogger(__name__)
LOGGING_FORMAT = '%(asctime)s %(name)s %(levelname)s %(message)s'


def parse_args():
    """parse command arguments"""
    parser = argparse.ArgumentParser()

    # commands
    parser.add_argument("--run", action="store_true", help="run collect loop",
                        required=True)

    # other options
    parser.add_argument("-d", "--debug", action="store_true",
                        help="enable debug")

    parser.add_argument("-f", "--config-file",
                        default="/etc/shine/ha.yaml",
                        help="main config file for shine-ha")

    parser.add_argument("-l", "--log-file",
                        default="/var/log/shine-ha.log",
                        help="logging file")

    return parser.parse_args()

def init_logger(log_file, debug):
    """initialize logger"""
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format=LOGGING_FORMAT,
                        filename=log_file)

    LOGGER.info('shine-ha starting')


class MainEventHandler(EventHandler):
    """shine-HA main event handler class"""

    def __init__(self, fsmon, lnetmon, port=None):
        EventHandler.__init__(self)
        self.fsmon = fsmon
        self.lnetmon = lnetmon
        self.port = port
        self.got_response = True # True the first time

    def ev_timer(self, timer):
        """ClusterShell timer fired at polling_interval..."""
        # Ensure that we got a response before triggering next shine status...
        if not self.got_response:
            msg = 'Skipping next status: previous status not received yet!'
            LOGGER.error(msg)
            return

        self.got_response = False

        # Check status of Lustre components using shine API in another thread
        StatusThread(self.fsmon.fs_name, self.port).start()

        # Check Lnet status
        self.lnetmon.ping()

    def ev_msg(self, port, msg):
        """ClusterShell async msg event"""
        # We received an update from a shine thread
        cmd, fs_conf, fs = msg

        if cmd == 'status':
            LOGGER.info('MainEventHandler.ev_msg: %s fs_name=%s', cmd,
                        fs.fs_name)
            if hasattr(fs, 'TEST_COMPLETED'): # just a hook for the tests
                task_terminate()
            else:
                self.got_response = True

                # LNet: set or update filesystem configuration
                self.lnetmon.fs_conf = fs_conf

                # Update FSMonitor instance with the resulting fs
                self.fsmon.update(fs_conf, fs)
        elif cmd == 'abort':
            LOGGER.info('MainEventHandler.ev_msg: abort')
            sys.exit(1)
        else:
            LOGGER.error('MainEventHandler.ev_msg: unrecognized cmd %s', cmd)


def start(fs_name, polling_interval, alert_mgr, comp_alert_thresolds,
          lnet_args):
    """Start shine-HA runloop"""
    # Get ClusterShell task object (thread specific)
    task = task_self()

    # FSMonitor receives fs status updates and generates alerts
    fsmon = FSMonitor(task, fs_name, alert_mgr, comp_alert_thresolds)

    # LNet Monitoring
    lnetmon = LNetMonitor(task, fs_name, alert_mgr, lnet_args)

    # Initialize main event handler
    meh = MainEventHandler(fsmon, lnetmon)

    # Create a task port to receive async messages from the action threads
    meh.port = task.port(handler=meh)

    # Install main monitor timer
    LOGGER.debug('starting monitoring timer with %.1fs interval',
                 polling_interval)
    task.timer(0, handler=meh, interval=polling_interval)

    # Start runloop
    task.run()

def main():
    """shine HA CLI entry point"""
    pargs = parse_args()
    assert pargs.run

    init_logger(pargs.log_file, pargs.debug)

    # Parse YAML config file
    LOGGER.info('loading config file "%s"', pargs.config_file)
    try:
        with open(pargs.config_file) as conff:
            confd = yaml.load(conff)
            LOGGER.debug('loaded configuration: %s', pprint.pformat(confd))
    except IOError as exc:
        LOGGER.error(exc)
        sys.exit(1)

    # Get main config options
    try:
        fs_name = confd['fs_name']
        inter_cfg = confd.get('polling_interval', DEFAULT_POLLING_INTERVAL)
        polling_interval = float(inter_cfg)

        # fs_monitor_state_count_thresholds
        if 'fs_monitor_state_count_thresholds' in confd:
            comp_alert_thresholds = confd['fs_monitor_state_count_thresholds']
        else:
            comp_alert_thresholds = DEFAULT_COMP_ALERT_THRESHOLDS

        lnet_args = confd.get('lnet_monitoring')

    except KeyError as exc:
        LOGGER.error('missing mandatory configuration keyword: %s', exc)
        sys.exit(1)

    try:
        start(fs_name, polling_interval, AlertManager.fromcfg(confd),
              comp_alert_thresholds, lnet_args)
    except KeyboardInterrupt:
        LOGGER.error('Exiting on KeyboardInterrupt')
        sys.exit(1)


if __name__ == '__main__':
    main()
