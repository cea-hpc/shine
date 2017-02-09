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
HA core decision-making module
"""

from operator import itemgetter
from itertools import groupby
import logging

from ClusterShell.Event import EventHandler
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import task_self

from Shine.HA.fsactions import StartThread
from Shine.HA.fsmon import STATE_IDTXT_MAP
from Shine.HA.alerts import Alert, ALERT_CLS_FS, ALERT_CLS_HA
from Shine.Lustre.Component import ComponentGroup
from Shine.Lustre.Component import MIGRATED, MOUNTED, CLIENT_ERROR, \
                                   TARGET_ERROR, RUNTIME_ERROR, OFFLINE, \
                                   NO_DEVICE, RECOVERING


DEFAULT_FENCE_CMD_TIMEOUT = 30

LOGGER = logging.getLogger(__name__)


class FenceHandler(EventHandler):
    """
    Server Fence Handler
    """
    def __init__(self, hacore, server):
        EventHandler.__init__(self)
        self.hacore = hacore
        self.server = server # fenced server

    def ev_read(self, worker):
        LOGGER.info('FenceHandler[%s](stdout): %s', self.server,
                    worker.current_msg)

    def ev_error(self, worker):
        LOGGER.warning('FenceHandler[%s](stderr): %s', self.server,
                       worker.current_errmsg)

    def ev_close(self, worker):
        if worker.did_timeout() or worker.current_rc != 0:
            self.hacore.fence_failed(self.server)
        else:
            self.hacore.fence_successful(self.server)


class HACore(Alert):
    """
    HACore is actually a stealth Alert class that listens for CRITICAL alerts
    and implement the Lustre failover logic.
    """

    def __init__(self, alert_mgr, mount_offline_targets=False,
                 unmount_error_targets=False,
                 migrate_targets_on_server_failure=False,
                 fence_command=None,
                 fence_command_timeout=DEFAULT_FENCE_CMD_TIMEOUT):
        Alert.__init__(self, self.__class__.__name__, sortkey=1000)

        # AlertManager cross reference: for accessing LNetMonitor and raising
        # our own Alerts.
        self.alert_mgr = alert_mgr

        # HA toggles
        self.mount_offline_targets = mount_offline_targets
        self.unmount_error_targets = unmount_error_targets
        self.migrate_targets_on_server_failure = \
            migrate_targets_on_server_failure

        # Server fencing command template
        self.fence_command = fence_command
        self.fence_timeout = fence_command_timeout

        # If both are set, failover is in progress
        # Failover servers and associated targets being migrated
        self.failover_servers = None
        self.failover_fs_name = None

    def info(self, aclass, message, ctx=None):
        if aclass == ALERT_CLS_FS and self.failover_servers:
            if ctx['FSMonitor'].state_optimal:
                LOGGER.info('HACore.info: fsmon reporting optimal state for '
                            '%s: failover completed.', ctx['fs_name'])
                self.failover_servers = None
                self.failover_fs_name = None

    def find_failover_servers(self, server, comps):
        """
        This method finds failover server(s) for the argument 'server' which
        usally is the one that failed. 'comps' should be all filesystem
        components.

        Return an iterator of tuple (failover server, associated components).
        """
        results = {}
        for comp in comps:
            if server not in comp._states:
                # Skip, this component doesn't run on our failed server.
                continue

            found = False
            for failserv, state in comp._states.items():
                if failserv == server:
                    continue
                # Look for offline (no error) states on the failover server
                if state in (OFFLINE, NO_DEVICE):
                    LOGGER.warning('Selected failover server %s in state %s '
                                   'for %s', failserv, STATE_IDTXT_MAP[state],
                                   comp.uniqueid())
                    results.setdefault(failserv, []).append(comp)
                    found = True
                    break
                else:
                    LOGGER.debug('Ignored failserver %s in state %s for %s',
                                 failserv, STATE_IDTXT_MAP[state],
                                 comp.uniqueid())

            if not found and comp.state not in (MOUNTED, MIGRATED):
                LOGGER.error('Unable to find any failover server for %s '
                             '(state %s)', comp.uniqueid(), comp.state)

        LOGGER.debug('find_failover_servers returned %s', results)
        return results

    def fence_and_migrate(self, fs_name, server, failover_servers):
        """Fence server and migrate targets to failover_servers."""
        LOGGER.warning('fence_and_migrate %s to %s', server,
                       NodeSet.fromlist(failover_servers.keys()))
        # Trigger failover
        msg = 'Target errors and lnet down on `%s`: triggering *failover*!' \
              % server
        ctx = {'failover_servers': failover_servers}
        self.alert_mgr.info(ALERT_CLS_HA, msg, ctx)

        # Set failover_servers (Failover now IN PROGRESS!)
        self.failover_servers = failover_servers
        self.failover_fs_name = fs_name

        # Fence node
        fence_eh = FenceHandler(self, server)
        fence_cmd = self.fence_command % server
        LOGGER.warning('Fence command timeout set to %ss', self.fence_timeout)
        LOGGER.warning('Executing: %s', fence_cmd)
        worker = task_self().shell(fence_cmd, handler=fence_eh,
                                   timeout=self.fence_timeout)
        worker.set_write_eof()

    def critical(self, aclass, message, ctx=None):
        """Critical alert received."""
        if aclass != ALERT_CLS_FS:
            return

        LOGGER.debug('HACore.critical %s %s %s', aclass, message, ctx)

        if self.failover_servers:
            LOGGER.warning('HACore.critical: failover already in progress (%s)',
                           self.failover_fs_name)
            return

        # First check components in error state, indeed we don't want to mount
        # an OST on a server with already full of OSTs in error.
        comps = ctx['FileSystem'].components.managed(inactive=True)

        servers = {}

        for comp in comps:
            sorted_states = sorted(comp._states.iteritems(), key=itemgetter(1))

            # Regroup by server
            for server, states in groupby(sorted_states, key=itemgetter(0)):
                statelist = list(st for node, st in states)
                LOGGER.debug('server=%s states=%s', server, statelist)
                servers.setdefault(server, set()).update(statelist)

        for server, states in servers.items():
            if states.issubset(set([RUNTIME_ERROR, TARGET_ERROR])):
                LOGGER.debug('All %s components from %s are in an error state',
                             ctx['fs_name'], server)

                # failover servers -> associated components
                failover_servers = self.find_failover_servers(server, comps)
                if not failover_servers:
                    LOGGER.error('No failover servers found, aborting.')
                    return

                # All components unreachable? Check LNET status
                server_down = (self.alert_mgr.lnetmon is not None and
                               self.alert_mgr.lnetmon.is_down(server))
                #server_down = True # XXX TEST XXX
                if server_down:
                    LOGGER.warning('Server %s is down and all components are '
                                   'in error', server)

                    if self.migrate_targets_on_server_failure:
                        self.fence_and_migrate(ctx['fs_name'], server,
                                               failover_servers)
                    else:
                        LOGGER.warning('migrate_targets_on_server_failure is '
                                       'not enabled; failover cancelled')
                else:
                    LOGGER.warning('Server %s is NOT down but all its '
                                   'components are in RUNTIME_ERROR', server)

            if states.issubset(set([TARGET_ERROR, RUNTIME_ERROR])):
                LOGGER.info('All components from %s are in errors', server)

    def fence_failed(self, server):
        LOGGER.error('Fence command failed for server %s: failover cannot '
                     'continue', server)
        self.failover_servers = None
        self.failover_fs_name = None

    def fence_successful(self, server):
        LOGGER.warning('Fence command successful for server %s', server)
        for server, complist in self.failover_servers.items():
            targets = NodeSet.fromlist(comp.uniqueid() for comp in complist)
            LOGGER.warning('Starting %s on %s', targets, server)
            # We cannot start resident and failover targets in one shot, so we
            # split them here.
            comps_resident = ComponentGroup()
            comps_foreign = ComponentGroup()
            for comp in complist:
                # Note: NodeSet is required for comp.failover()
                changed = comp.failover(NodeSet(server))
                LOGGER.warning('comp.failover(%s) for %s returned %s',
                               comp.uniqueid(), server, changed)
                LOGGER.debug('comp.server.hostname=%s', comp.server.hostname)
                if changed:
                    comps_foreign.add(comp)
                else:
                    comps_resident.add(comp)

            if comps_resident:
                LOGGER.warning('Launching StartThread for resident components')
                StartThread(self.failover_fs_name, self.alert_mgr.reply_port,
                            comps_resident).start()

            if comps_foreign:
                LOGGER.warning('Launching StartThread for foreign components')
                StartThread(self.failover_fs_name, self.alert_mgr.reply_port,
                            comps_foreign, failover=server).start()
