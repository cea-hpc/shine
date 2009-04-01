# FileSystem.py -- Lustre FS
# Copyright (C) 2007, 2008, 2009 CEA
#
# This file is part of shine
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# $Id$

"""
Lustre FileSystem class.

Represents a Lustre FS.
"""

import copy
from sets import Set
import socket

from ClusterShell.NodeSet import NodeSet, RangeSet

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

# Action exceptions
from Actions.Action import ActionErrorException
from Actions.Proxies.ProxyAction import *

from Actions.Install import Install
from Actions.Proxies.Preinstall import Preinstall
from Actions.Proxies.FSProxyAction import FSProxyAction
from Actions.Proxies.FSClientProxyAction import FSClientProxyAction

from EventHandler import *
from Client import *
from Server import *
from Target import *


class FSException(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class FSError(FSException):
    """
    Base FileSystem error exception.
    """

class FSSyntaxError(FSError):
    def __init__(self, message):
        self.message = "Syntax error: \"%s\"" % (message)
    def __str__(self):
        return self.message

class FSBadTargetError(FSSyntaxError):
    def __init__(self, target_name):
        self.message = "Syntax error: unrecognized target \"%s\"" % (target_name)

class FSStructureError(FSError):
    """
    Lustre file system structure error, raised after an invalid configuration
    is encountered. For example, you will get this error if you try to assign
    two targets `MGT' to a filesystem.
    """

class FSRemoteError(FSError):
    """
    Remote host(s) not available, or a remote operation failed.
    """
    def __init__(self, nodes, rc, message):
        FSError.__init__(self, message)
        self.nodes = nodes
        self.rc = int(rc)

    def __str__(self):
        return "%s: %s [rc=%d]" % (self.nodes, self.message, self.rc)


STATUS_SERVERS      = 0x01
STATUS_HASERVERS    = 0x02
STATUS_CLIENTS      = 0x10
STATUS_ANY          = 0xff


class FileSystem:
    """
    The Lustre FileSystem abstract class.
    """

    def __init__(self, fs_name, event_handler=None):
        self.fs_name = fs_name
        self.debug = False
        self.set_eventhandler(event_handler)
        self.proxy_errors = []

        self.local_hostname = socket.gethostname()
        self.local_hostname_short = self.local_hostname.split('.', 1)[0]

        # file system MGT
        self.mgt = None

        # All FS server targets (MGT, MDT, OST...)
        self.targets = []

        # All FS clients
        self.clients = []

        # filled after successful install
        self.mgt_servers = NodeSet()
        self.mgt_count = 0

        self.mdt_servers = NodeSet()
        self.mdt_count = 0

        self.ost_servers = NodeSet()
        self.ost_count = 0

        self.target_count = 0
        self.target_servers = NodeSet()

    def set_debug(self, debug):
        self.debug = debug

    #
    # file system event handling
    #

    def _invoke_event(self, event, **kwargs):
        if 'target' in kwargs or 'client' in kwargs:
            kwargs.setdefault('node', None)
        getattr(self.event_handler, event)(**kwargs)

    def _invoke_dummy(self, event, **kwargs):
        pass

    def set_eventhandler(self, event_handler):
        self.event_handler = event_handler
        if self.event_handler is None:
            self._invoke = self._invoke_dummy
        else:
            self._invoke = self._invoke_event

    def _handle_shine_event(self, event, node, **params):
        #print "_handle_shine_event %s %s" % (event, params)
        target = params.get('target')
        if target:
            found = False
            for t in self.targets:
                if t.match(target):
                    # perform sanity checks here
                    old_nids = t.get_nids()
                    if old_nids != target.get_nids():
                        print "NIDs mismatch %s -> %s" % \
                                (','.join(old.nids), ','.join(target.get_nids))
                    # update target from remote one
                    t.update(target)
                    # substitute target parameter by local one
                    params['target'] = t
                    found = True
            if not found:
                print "Target Update FAILED (%s)" % target
        
        client = params.get('client')
        if client:
            found = False
            for c in self.clients:
                if c.match(client):
                    # update client from remote one
                    c.update(client)
                    # substitute client parameter
                    params['client'] = c
                    found = True
            if not found:
                print "Client Update FAILED (%s)" % client

        self._invoke(event, node=node, **params)

    def _handle_shine_proxy_error(self, nodes, message):
        self.proxy_errors.append((NodeSet(nodes), message))

    #
    # file system construction
    #

    def _attach_target(self, target):
        self.targets.append(target)
        if target.type == 'mgt':
            self.mgt = target
        self._update_structure()

    def _attach_client(self, client):
        self.clients.append(client)
        self._update_structure()

    def new_target(self, server, type, index, dev, jdev=None, group=None,
            tag=None, enabled=True):
        """
        Create a new attached target.
        """
        #print "new_target on %s type %s (enabled=%s)" % (server, type, enabled)

        if type == 'mgt' and self.mgt and len(self.mgt.get_nids()) > 0:
            raise FSStructureError("A Lustre FS has only one MGT.")

        # Instantiate matching target class (eg. 'ost' -> OST).
        target = getattr(sys.modules[self.__class__.__module__], type.upper())(fs=self,
                server=server, index=index, dev=dev, jdev=jdev, group=group, tag=tag,
                enabled=enabled)
        
        return target

    def new_client(self, server, mount_path, enabled=True):
        """
        Create a new attached client.
        """
        client = Client(self, server, mount_path, enabled)

        return client

    def get_mgs_nids(self):
        return self.mgt.get_nids()
    
    def get_client_servers(self):
        return NodeSet.fromlist([c.server for c in self.clients])

    def get_client_statecounters(self):
        """
        Get (ignored, offline, error, runtime_error, mounted) client state counters tuple.
        """
        ignored = 0
        states = {}
        for client in self.clients:
            if client.action_enabled:
                state = states.setdefault(client.state, 0)
                states[client.state] = state + 1
            else:
                ignored += 1
        
        return (ignored,
                states.get(OFFLINE, 0),
                states.get(CLIENT_ERROR, 0),
                states.get(RUNTIME_ERROR, 0),
                states.get(MOUNTED, 0))

    def targets_by_state(self, state):
        for target in self.targets:
            #print target, target.state
            if target.action_enabled and target.state == state:
                yield target

    def target_servers_by_state(self, state):
        servers = NodeSet()
        for target in self.targets_by_state(state):
            #print "OK %s" % target
            servers.add(target.servers[0])
        return servers

    def _distant_action_by_server(self, action_class, servers, **kwargs):

        task = task_self()

        # filter local server
        if self.local_hostname in servers:
            distant_servers = servers.difference(self.local_hostname)
        elif self.local_hostname_short in servers:
            distant_servers = servers.difference(self.local_hostname_short)
        else:
            distant_servers = servers

        # perform action on distant servers
        if len(distant_servers) > 0:
            action = action_class(nodes=distant_servers, fs=self, **kwargs)
            action.launch()
            task.resume()

    def install(self, fs_config_file, nodes=None):
        """
        Install FS config files.
        """
        servers = NodeSet()

        for target in self.targets:
            # install on failover partners too
            for s in target.servers:
                if not nodes or s in nodes:
                    servers.add(s)

        for client in self.clients:
            # install on failover partners too
            if not nodes or client.server in nodes:
                servers.add(client.server)

        assert len(servers) > 0, "no servers?"

        try:
            self._distant_action_by_server(Preinstall, servers)
            self._distant_action_by_server(Install, servers, config_file=fs_config_file)
        except ProxyActionError, e:
            # switch to public exception
            raise FSRemoteError(e.nodes, e.rc, e.message)
        
    def remove(self):
        """
        Remove FS config files.
        """

        result = 0

        servers = NodeSet()

        self.action_refcnt = 0
        self.proxy_errors = []

        # iterate over lustre servers
        for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():
            if not e_s_targets:
                continue

            if server.is_local():
                # remove local fs configuration file
                conf_dir_path = Globals().get_conf_dir()
                fs_file = os.path.join(Globals().get_conf_dir(), "%s.xmf" % self.fs_name)
                rc = os.unlink(fs_file)
                result = max(result, rc)
            else:
                servers.add(server)

        if len(servers) > 0:
            # Perform the remove operations on all targets for these nodes.
            action = FSProxyAction(self, 'remove', servers, self.debug)
            action.launch()
            self.action_refcnt += 1

        task_self().resume()

        if self.proxy_errors:
            return RUNTIME_ERROR
        
        return result

    def _update_structure(self):
        # convenience
        for type, targets, servers in self._iter_targets_servers_by_type():
            if type == 'ost':
                self.ost_count = len(targets)
                self.ost_servers = NodeSet(servers)
            elif type == 'mdt':
                self.mdt_count = len(targets)
                self.mdt_servers = NodeSet(servers)
            elif type == 'mgt':
                self.mgt_count = len(targets)
                self.mgt_servers = NodeSet(servers)

        self.target_count = self.mgt_count + self.mdt_count + self.ost_count
        self.target_servers = self.mgt_servers | self.mdt_servers | self.ost_servers

    def _iter_targets_servers_by_type(self, reverse=False):
        """
        Per type of target iterator : returns a tuple (list of targets,
        list of servers) per target type.
        """
        last_target_type = None
        servers = NodeSet()
        targets = Set()

        #self.targets.sort()

        if reverse:
            self.targets.reverse()

        for target in self.targets:
            if last_target_type and last_target_type != target.type:
                # type of target changed, commit actions
                if len(targets) > 0:
                    yield last_target_type, targets, servers
                    servers.clear()     # ClusterShell 1.1+ needed (sorry)
                    targets.clear()

            if target.action_enabled:
                targets.add(target)
                # select server: change master_server for -F node
                servers.add(target.get_selected_server())
            last_target_type = target.type

        if len(targets) > 0:
            yield last_target_type, targets, servers

    def targets_by_type(self, reverse=False):
        """
        Per type of target iterator : returns the following tuple:
        (type, (list of all targets of this type, list of enabled targets))
        per target type.
        """
        last_target_type = None
        a_targets = Set()
        e_targets = Set()

        for target in self.targets:
            if last_target_type and last_target_type != target.type:
                # type of target changed, commit actions
                if len(a_targets) > 0:
                    yield last_target_type, (a_targets, e_targets)
                    a_targets.clear()
                    e_targets.clear()

            a_targets.add(target)
            if target.action_enabled:
                e_targets.add(target)
            last_target_type = target.type

        if len(a_targets) > 0:
            yield last_target_type, (a_targets, e_targets)

    def _iter_targets_by_server(self):
        """
        Per server of target iterator : returns the following tuple:
        (server, (list of all server targets, list of enabled targets))
        per target server.
        """
        servers = {}
        for target in self.targets:
            a_targets, e_targets = servers.setdefault(target.get_selected_server(), (Set(), Set()))
            a_targets.add(target)
            if target.action_enabled:
                e_targets.add(target)

        return servers.iteritems()


    def _iter_type_idx_for_targets(self, targets):
        last_target_type = None

        indexes = RangeSet(autostep=3)

        #self.targets.sort()

        for target in targets:
            if last_target_type and last_target_type != target.type:
                # type of target changed, commit actions
                if len(indexes) > 0:
                    yield last_target_type, indexes
                    indexes.clear()     # CS 1.1+
            indexes.add(int(target.index))
            last_target_type = target.type

        if len(indexes) > 0:
            yield last_target_type, indexes

    def format(self, **kwargs):

        # Remember format launched, so we can check their status once
        # all operations are done.
        format_launched = Set()

        servers_formatall = NodeSet()

        self.proxy_errors = []
        self.action_refcnt = 0

        for server, (a_targets, e_targets) in self._iter_targets_by_server():

            if server.is_local():
                # local server
                for target in e_targets:
                    target.format(**kwargs)
                    self.action_refcnt += 1

                format_launched.update(e_targets)

            else:
                # distant server
                if len(a_targets) == len(e_targets):
                    # group in one action if "format all targets on this server"
                    # is detected
                    servers_formatall.add(server)
                else:
                    # otherwise, format per selected targets on this server
                    for t_type, t_rangeset in \
                            self._iter_type_idx_for_targets(e_targets):
                        action = FSProxyAction(self, 'format',
                                NodeSet(server), self.debug, t_type, t_rangeset)
                        action.launch()
                        self.action_refcnt += 1

                format_launched.update(e_targets)

        if len(servers_formatall) > 0:
            action = FSProxyAction(self, 'format', servers_formatall, self.debug)
            action.launch()
            self.action_refcnt += 1

        task_self().resume()

        if self.proxy_errors:
            return RUNTIME_ERROR

        # Ok, workers have completed, perform late status check.
        for target in format_launched:
            if target.state != OFFLINE:
                return target.state

        return OFFLINE

    def status(self, flags=STATUS_ANY):
        """
        Get status of filesystem.
        """

        status_target_launched = Set()
        status_client_launched = Set()
        servers_statusall = NodeSet()
        self.action_refcnt = 0
        self.proxy_errors = []

        # prepare servers status checks
        if flags & STATUS_SERVERS:
            for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():
                if len(e_s_targets) == 0:
                    continue

                if server.is_local():
                    for target in e_s_targets:
                        target.status()
                        self.action_refcnt += 1
                    status_target_launched.update(e_s_targets)
                else:
                    # distant server: check if all server targets have been selected
                    if len(a_s_targets) == len(e_s_targets):
                        # "status on all targets for this server" detected
                        servers_statusall.add(server)
                    else:
                        # status per selected targets on this server
                        for t_type, t_rangeset in \
                                self._iter_type_idx_for_targets(e_s_targets):
                            action = FSProxyAction(self, 'status',
                                    NodeSet(server), self.debug, t_type, t_rangeset)
                            action.launch()
                            self.action_refcnt += 1
                    status_target_launched.update(e_s_targets)

        # prepare clients status checks
        if flags & STATUS_CLIENTS:
            for client in self.clients:
                if client.action_enabled:
                    server = client.server
                    if server.is_local():
                        client.status()
                        self.action_refcnt += 1
                    elif server not in servers_statusall:
                        servers_statusall.add(server)
                    status_client_launched.add(client)

        # launch distant actions
        if len(servers_statusall) > 0:
            action = FSProxyAction(self, 'status', servers_statusall, self.debug)
            action.launch()
            self.action_refcnt += 1

        # run loop
        task_self().resume()
        
        # return a dict of {state : target list}
        rdict = {}

        # all launched targets+clients
        launched = (status_target_launched | status_client_launched)
        if self.proxy_errors:
            # find targets/clients affected by the runtime error(s)
            for target in launched:
                for nodes, msg in self.proxy_errors:
                    if target.server in nodes:
                        target.state = RUNTIME_ERROR

        for target in launched:
            assert target.state != None
            targets = rdict.setdefault(target.state, [])
            targets.append(target)
        return rdict

    def status_target(self, target):
        """
        Launch a status request for a specific local or remote target.
        """

        # Don't call me if the target itself is not enabled.
        assert target.action_enabled

        server = target.get_selected_server()

        if server.is_local():
            # Target is local
            target.status()
        else:
            action = FSProxyAction(self, 'status', NodeSet(server), self.debug,
                    target.type, RangeSet(str(target.index)))
            action.launch()

        self.action_refcnt = 1
        task_self().resume()

    def start(self, **kwargs):
        """
        Start Lustre file system servers.
        """
        self.proxy_errors = []

        # What starting order to use?
        for target in self.targets:
            if isinstance(target, MDT) and target.action_enabled:
                # Found enabled MDT: perform writeconf check.
                self.status_target(target)
                if target.has_first_time_flag() or target.has_writeconf_flag():
                    # first_time or writeconf flag found, start MDT before OSTs
                    MDT.target_order = 2 # change MDT class variable order

        self.targets.sort()

        # servers_startall is used for optimization, it contains nodes
        # where we have to perform the start operation on all targets
        # found for this FS. This will limit the number of FSProxyAction
        # to spawn.
        servers_startall = NodeSet()

        # Remember targets launched, so we can check their status once
        # all operations are done (here, status are checked after all
        # targets of the same type have completed the start operation -
        # with possible failure).
        targets_launched = Set()

        # Keep number of actions in order to abort task correctly in
        # action's ev_close.
        self.action_refcnt = 0

        result = 0

        # iterate over targets by type
        for type, (a_targets, e_targets) in self.targets_by_type():
            
            if not e_targets:
                # no target of this type is enabled
                continue

            # iterate over lustre servers
            for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():

                # To summary, we keep targets that are:
                # 1. enabled
                # 2. of according type
                # 3. on this server
                type_e_targets = e_targets.intersection(e_s_targets)
                if len(type_e_targets) == 0:
                    # skip as no target of this type is enabled on this server
                    continue

                if server.is_local():
                    # Start targets if we are on the good server.
                    for target in type_e_targets:
                        # Note that target.start() should never block here:
                        # it will perform necessary non-blocking actions and
                        # (when needed) will start local ClusterShell workers.
                        target.start(**kwargs)
                        self.action_refcnt += 1
                else:
                    assert a_s_targets.issuperset(type_e_targets)
                    assert len(type_e_targets) > 0

                    # Distant server: for code and requests optimizations,
                    # we check when all server targets have been selected.
                    if len(type_e_targets) == len(a_s_targets):
                        # "start all FS targets on this server" detected
                        servers_startall.add(server)
                    else:
                        # Start per selected targets on this server.
                        for t_type, t_rangeset in \
                                self._iter_type_idx_for_targets(type_e_targets):
                            action = FSProxyAction(self, 'start',
                                    NodeSet(server), self.debug, t_type, t_rangeset)
                            action.launch()
                            self.action_refcnt += 1

                # Remember launched targets of this server for late status check.
                targets_launched.update(type_e_targets)

            if len(servers_startall) > 0:
                # Perform the start operations on all targets for these nodes.
                action = FSProxyAction(self, 'start', servers_startall, self.debug)
                action.launch()
                self.action_refcnt += 1

            # Resume current task, ie. start runloop, process workers events
            # and also act as a target-type barrier.
            task_self().resume()

            if self.proxy_errors:
                return RUNTIME_ERROR

            # Ok, workers have completed, perform late status check...
            for target in targets_launched:
                if target.state > result:
                    result = target.state
                    if result > RECOVERING:
                        # Avoid broken cascading starts, so we break now if
                        # a target of the previous type failed to start.
                        return result

            # Some needed cleanup before next target type.
            servers_startall.clear()
            targets_launched.clear()

        return result


    def stop(self, **kwargs):
        """
        Stop file system.
        """
        rc = MOUNTED

        # Stop: reverse order
        self.targets.sort()
        self.targets.reverse()

        # servers_stopall is used for optimization, see the comment in
        # start() for servers_startall.
        servers_stopall = NodeSet()

        # Remember targets when stop was launched.
        targets_stopping = Set()

        self.action_refcnt = 0
        self.proxy_errors = []

        # We use a similar logic than start(): see start() for comments.
        # iterate over targets by type
        for type, (a_targets, e_targets) in self.targets_by_type():

            if not e_targets:
                # no target of this type is enabled
                continue

            # iterate over lustre servers
            for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():
                type_e_targets = e_targets.intersection(e_s_targets)
                if len(type_e_targets) == 0:
                    # skip as no target of this type is enabled on this server
                    continue

                if server.is_local():
                    # Stop targets if we are on the good server.
                    for target in type_e_targets:
                        target.stop(**kwargs)
                        self.action_refcnt += 1
                else:
                    assert a_s_targets.issuperset(type_e_targets)
                    assert len(type_e_targets) > 0

                    # Distant server: for code and requests optimizations,
                    # we check when all server targets have been selected.
                    if len(type_e_targets) == len(a_s_targets):
                        # "stop all FS targets on this server" detected
                        servers_stopall.add(server)
                    else:
                        # Stop per selected targets on this server.
                        for t_type, t_rangeset in \
                                self._iter_type_idx_for_targets(type_e_targets):
                            action = FSProxyAction(self, 'stop',
                                    NodeSet(server), self.debug, t_type, t_rangeset)
                            action.launch()
                            self.action_refcnt += 1

                # Remember launched stopping targets of this server for late status check.
                targets_stopping.update(type_e_targets)

            if len(servers_stopall) > 0:
                # Perform the stop operations on all targets for these nodes.
                action = FSProxyAction(self, 'stop', servers_stopall, self.debug)
                action.launch()
                self.action_refcnt += 1

            task_self().resume()

            if self.proxy_errors:
                return RUNTIME_ERROR

            # Ok, workers have completed, perform late status check...
            for target in targets_stopping:
                if target.state > rc:
                    rc = target.state

            # Some needed cleanup before next target type.
            servers_stopall.clear()
            targets_stopping.clear()

        return rc

    def mount(self, **kwargs):
        """
        Mount FS clients.
        """
        servers_mountall = NodeSet()
        clients_mounting = Set()
        self.action_refcnt = 0
        self.proxy_errors = []

        for client in self.clients:

            if not client.action_enabled:
                continue

            if client.server.is_local():
                # local client
                client.start(**kwargs)
                self.action_refcnt += 1
            else:
                # distant client
                servers_mountall.add(client.server)

            clients_mounting.add(client)

        if len(servers_mountall) > 0:
            action = FSClientProxyAction(self, 'mount', servers_mountall, self.debug)
            action.launch()
            self.action_refcnt += 1

        task_self().resume()

        if self.proxy_errors:
            return RUNTIME_ERROR

        # Ok, workers have completed, perform late status check...
        for client in clients_mounting:
            if client.state != MOUNTED:
                return client.state

        return MOUNTED

    def umount(self, **kwargs):
        """
        Unmount FS clients.
        """
        servers_umountall = NodeSet()
        clients_umounting = Set()
        self.action_refcnt = 0
        self.proxy_errors = []

        for client in self.clients:

            if not client.action_enabled:
                continue

            if client.server.is_local():
                # local client
                client.stop(**kwargs)
                self.action_refcnt += 1
            else:
                # distant client
                servers_umountall.add(client.server)

            clients_umounting.add(client)

        if len(servers_umountall) > 0:
            action = FSClientProxyAction(self, 'umount', servers_umountall, self.debug)
            action.launch()
            self.action_refcnt += 1

        task_self().resume()

        if self.proxy_errors:
            return RUNTIME_ERROR

        # Ok, workers have completed, perform late status check...
        for client in clients_umounting:
            if client.state != OFFLINE:
                return client.state

        return OFFLINE

    def info(self):
        pass

    def tune(self, tuning_model):
        """
        Tune server.
        """
        task = task_self()
        tune_all = NodeSet()
        type_map = { 'mgt': 'mgs', 'mdt': 'mds', 'ost' : 'oss' }
        self.action_refcnt = 0
        self.proxy_errors = []
        result = 0

        # Install tuning.conf on enabled distant servers
        for server, (a_targets, e_targets) in self._iter_targets_by_server():
            if e_targets and not server.is_local():
                tune_all.add(server)
        if len(tune_all) > 0:
            self._distant_action_by_server(Install, tune_all, config_file=Globals().get_tuning_file())
            self.action_refcnt += 1
            task.resume()
            tune_all.clear()

        # Apply tunings
        self.action_refcnt = 0
        for server, (a_targets, e_targets) in self._iter_targets_by_server():
            if not e_targets:
                continue
            if server.is_local():
                types = Set()
                for t in e_targets:
                    types.add(type_map[t.type])

                rc = server.tune(tuning_model, types, self.fs_name)
                result = max(result, rc)
            else:
                # distant server
                if len(a_targets) == len(e_targets):
                    # group in one action
                    tune_all.add(server)
                else:
                    # otherwise, tune per selected targets on this server
                    for t_type, t_rangeset in \
                            self._iter_type_idx_for_targets(e_targets):
                        action = FSProxyAction(self, 'tune',
                                NodeSet(server), self.debug, t_type, t_rangeset)
                        action.launch()
                        self.action_refcnt += 1

        if len(tune_all) > 0:
            action = FSProxyAction(self, 'tune', tune_all, self.debug)
            action.launch()
            self.action_refcnt += 1

        task.resume()

        if self.proxy_errors:
            return RUNTIME_ERROR

        return result

