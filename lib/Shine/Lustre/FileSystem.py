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
from Actions.Proxies.ProxyAction import ProxyActionError

from Actions.Install import Install
from Actions.Proxies.Preinstall import Preinstall
from Actions.Proxies.FSProxyAction import FSProxyAction
from Actions.Proxies.FSClientProxyAction import FSClientProxyAction

from EventHandler import *
from Server import *
from Target import *
import Client


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

        self.local_hostname = socket.gethostname()
        self.local_hostname_short = self.local_hostname.split('.', 1)[0]

        # file system MGT
        self.mgt = None

        # All FS server targets (MGT, MDT, OST...)
        self.targets = []

        # All FS clients
        self.clients = []

        # filled after successful install
        self.mgt_servers = None
        self.mgt_count = 0

        self.mdt_servers = None
        self.mdt_count = 0

        self.ost_servers = None
        self.ost_count = 0

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
        client = Client.Client(self, server, mount_path, enabled)

        return client

    def get_mgs_nids(self):
        return self.mgt.get_nids()
    
    def get_client_servers(self):
        return NodeSet.fromlist([c.server for c in self.clients])

    def get_client_statecounters(self):
        """
        Get (ignored, down, loaded, mounted) client state counters tuple.
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
                states.get(Client.DOWN, 0),
                states.get(Client.LOADED, 0),
                states.get(Client.MOUNTED, 0))

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
            self._distant_action_by_server(Install, servers, fs_config_file=fs_config_file)
        except ProxyActionError, e:
            # switch to public exception
            raise FSRemoteError(e.nodes, e.rc, e.message)
        
        #self._update_target_counters()

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

        servers_formatall = NodeSet()

        for server, (a_targets, e_targets) in self._iter_targets_by_server():
            #print "S: %s %s %s" % (server, a_targets, e_targets)
            
            if server.is_local():
                for target in e_targets:
                    target.format(**kwargs)
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

        if len(servers_formatall) > 0:
            action = FSProxyAction(self, 'format', servers_formatall, self.debug)
            action.launch()

        try:
            task_self().resume()
        except ProxyActionError, e:
            # switch to public exception
            raise FSRemoteError(e.nodes, e.rc, e.message)

        servers_formatall.clear()

        # Ok, workers have completed, perform late status check...
        #for target in targets_launched:
        #    if target.state < MOUNT_RECOVERY:
        #        # Avoid broken cascading starts, so we break now if any
        #        # target of previous type failed to start.
        #        return False



    """
    def _launch_target_action_on_servers(self, local_action, distant_action, targets, servers):
        # start selected servers
        print "targets %s" % targets[0].type

        local_server = None

        if self.local_hostname in servers:
            distant_servers = servers.difference(self.local_hostname)
            local_server = self.local_hostname
        elif self.local_hostname_short in servers:
            distant_servers = servers.difference(self.local_hostname_short)
            local_server = self.local_hostname_short
        else:
            distant_servers = servers

        if local_server:
            for target in targets:
                if str(target.master_server) == local_server:
                    getattr(target, local_action)()

        if len(distant_servers) > 0:
            print "distant %s" % distant_servers

            #Format(distant_servers, target, indexes, self)
            #print binascii.b2a_base64(pickle.dumps(targets, -1))

            #Actions.Proxies.Start.Start(distant_servers)
    """
    
    def status(self, flags=STATUS_ANY):
        """
        Get status of filesystem.
        """

        servers_statusall = NodeSet()

        # prepare servers status checks
        if flags & STATUS_SERVERS:
            for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():
                if len(e_s_targets) == 0:
                    continue

                if server.is_local():
                    for target in e_s_targets:
                        target.status()
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

        # prepare clients status checks
        if flags & STATUS_CLIENTS:
            for client in self.clients:
                if client.action_enabled:
                    server = client.server
                    if server.is_local():
                        client.status()
                    elif server not in servers_statusall:
                        servers_statusall.add(server)

        # launch distant actions
        if len(servers_statusall) > 0:
            action = FSProxyAction(self, 'status', servers_statusall, self.debug)
            action.launch()

        # runloop
        try:
            task_self().resume()
        except ProxyActionError, e:
            # switch to public exception
            servers_statusall.clear()
            raise FSRemoteError(e.nodes, e.rc, e.message)
        
        servers_statusall.clear()

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
            #target.check()
        else:
            action = FSProxyAction(self, 'status', NodeSet(server), self.debug,
                    target.type, RangeSet(str(target.index)))
            action.launch()

        try:
            task_self().resume()
        except ProxyActionError, e:
            # switch to public exception
            raise FSRemoteError(e.nodes, e.rc, e.message)

    def start(self, **kwargs):
        """
        Start Lustre file system servers.
        """

        # What starting order to use?
        for target in self.targets:
            if isinstance(target, MDT) and target.action_enabled:
                # Found enabled MDT: perform writeconf check.
                self.status_target(target)
                if target.has_first_time_flag() or target.has_writeconf_flag():
                    # first_time or writeconf flag found, start MDT before OSTs
                    MDT.target_order = 2 # change MDT class variable order
                    break
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

        # iterate over targets by type
        for type, (a_targets, e_targets) in self.targets_by_type():
            
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

                # Remember launched targets of this server for late status check.
                targets_launched.update(type_e_targets)

            if len(servers_startall) > 0:
                # Perform the start operations on all targets for these nodes.
                action = FSProxyAction(self, 'start', servers_startall, self.debug)
                action.launch()

            # Resume current task, ie. start runloop, process workers events
            # and also act as a target-type barrier.
            try:
                task_self().resume()
            except ProxyActionError, e:
                # something wrong occured, switch to public exception
                raise FSRemoteError(e.nodes, e.rc, e.message)

            # Ok, workers have completed, perform late status check...
            for target in targets_launched:
                if target.state < MOUNT_RECOVERY:
                    # Avoid broken cascading starts, so we break now if
                    # a target of the previous type failed to start.
                    return False

            # Some needed cleanup before next target type.
            servers_startall.clear()
            targets_launched.clear()

        return True


    def stop(self, **kwargs):
        """
        Stop file system.
        """
        ok = True

        # Stop: reverse order
        self.targets.sort()
        self.targets.reverse()

        # servers_stopall is used for optimization, see the comment in
        # start() for servers_startall.
        servers_stopall = NodeSet()

        # Remember targets when stop was launched.
        targets_stopping = Set()

        # We use a similar logic than start(): see start() for comments.
        # iterate over targets by type
        for type, (a_targets, e_targets) in self.targets_by_type():
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

                # Remember launched stopping targets of this server for late status check.
                targets_stopping.update(type_e_targets)

            if len(servers_stopall) > 0:
                # Perform the stop operations on all targets for these nodes.
                action = FSProxyAction(self, 'stop', servers_stopall, self.debug)
                action.launch()

            try:
                task_self().resume()
            except ProxyActionError, e:
                raise FSRemoteError(e.nodes, e.rc, e.message)

            # Ok, workers have completed, perform late status check...
            for target in targets_stopping:
                if target.state > DOWN:
                    # Avoid broken cascading stop?
                    ok = False
                    print "WRONG state %d for %s" % (target.state, target.dev)
                    break

            # Some needed cleanup before next target type.
            servers_stopall.clear()
            targets_stopping.clear()

        return ok

    def mount(self, **kwargs):
        """
        """
        servers_mountall = NodeSet()

        for client in self.clients:

            if not client.action_enabled:
                continue

            if client.server.is_local():
                # local client
                client.start(**kwargs)
            else:
                # distant client
                servers_mountall.add(client.server)

        if len(servers_mountall) > 0:
            action = FSClientProxyAction(self, 'mount', servers_mountall, self.debug)
            action.launch()

        try:
            task_self().resume()
        except ProxyActionError, e:
            # switch to public exception
            servers_mountall.clear()
            raise FSRemoteError(e.nodes, e.rc, e.message)

        servers_mountall.clear()

    def umount(self, **kwargs):
        """
        """
        servers_umountall = NodeSet()

        for client in self.clients:

            if not client.action_enabled:
                continue

            if client.server.is_local():
                # local client
                client.stop(**kwargs)
            else:
                # distant client
                servers_umountall.add(client.server)

        if len(servers_umountall) > 0:
            action = FSClientProxyAction(self, 'umount', servers_umountall, self.debug)
            action.launch()

        try:
            task_self().resume()
        except ProxyActionError, e:
            # switch to public exception
            servers_umountall.clear()
            raise FSRemoteError(e.nodes, e.rc, e.message)

        servers_umountall.clear()

    def info(self):
        pass

    def tune(self, tuning_model):
        """
        Tune server.
        """
        tune_all = NodeSet()
        type_map = { 'mgt': 'mgs', 'mdt': 'mds', 'ost' : 'oss' }

        for server, (a_targets, e_targets) in self._iter_targets_by_server():
            
            if server.is_local():
                types = Set()
                for t in e_targets:
                    types.add(type_map[t.type])

                server.tune(tuning_model, types, self.fs_name)
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

        if len(tune_all) > 0:
            action = FSProxyAction(self, 'tune', tune_all, self.debug)
            action.launch()

        try:
            task_self().resume()
        except ProxyActionError, e:
            # switch to public exception
            raise FSRemoteError(e.nodes, e.rc, e.message)

        tune_all.clear()

