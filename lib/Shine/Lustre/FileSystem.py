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

from itertools import ifilter, imap, groupby
from operator import attrgetter

from ClusterShell.NodeSet import NodeSet, RangeSet

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

# Action exceptions
from Actions.Action import ActionErrorException
from Actions.Proxies.ProxyAction import *

from Actions.Install import Install
from Actions.Proxies.Preinstall import Preinstall
from Actions.Proxies.FSProxyAction import FSProxyAction

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
                   tag=None, enabled=True, mode='managed'):
        """
        Create a new attached target.
        """
        #print "new_target on %s type %s (enabled=%s)" % (server, type, enabled)
        if type not in [ 'mgt', 'mdt', 'ost' ]:
            raise FSBadTargetError(type)

        if type == 'mgt' and self.mgt and len(self.mgt.get_nids()) > 0:
            raise FSStructureError("A Lustre FS has only one MGT.")

        # Instantiate matching target class (eg. 'ost' -> OST).
        target = getattr(sys.modules[self.__class__.__module__], type.upper())(fs=self,
                server=server, index=index, dev=dev, jdev=jdev, group=group, tag=tag,
                enabled=enabled, mode=mode)
        
        return target

    def new_client(self, server, mount_path, enabled=True):
        """
        Create a new attached client.
        """
        client = Client(self, server, mount_path, enabled)

        return client

    #
    # Iterators over filesystem components
    #

    def enabled_clients(self):
        """Iterator over all enabled clients"""
        # Optimized version of:
        #   for client in self.clients:
        #     if client.action_enabled:
        #       yield client

        # FIXME: Add filtering and grouping support like enabled_targets()
        return ifilter(attrgetter("action_enabled"), self.clients)

    def enabled_targets(self, group_attr=None, group_key=None, filter_key=None, reverse=False):
        """This function returns an iterator over enabled targets with 3 
        additionnal possibilities:
        - Filter targets more precisely (using filter_key)
        - Group results by attributes or key (using group_attr or group_key)
        - Reverse results (using reverse)
        All can be combined.

        Example #1: Iterate over enabled OSTs only:
         self.enabled_targets(filter_key=lambda t: t.type == "ost")

        Example #2: Group target by server
         self.enabled_targets(group_attr="server")

        Example #3: Group using 2 criterias, first type and then server
         key = lambda t: (t.type, t.server)
         self.enabled_targets(group_key=key)
        """

        # Try to construct a grouping key.
        # If a groupping attribute is provided, use this name to build
        # the group_key. If a group_key is provided, ignore group_attr.
        #
        # See: Python documentation about itertools.groupby and sorted()
        if not group_key:
            if group_attr:
                group_key = attrgetter(group_attr)

        if group_key:
            # A grouping is needed, sort the target using this key,
            # and then group results using the same key.
            sortlist = sorted(self.enabled_targets(filter_key=filter_key), \
                              key=group_key, reverse=reverse)
            return groupby(sortlist, group_key)
        else:
            # As we do not group and sort, reverse has no meaning here
            assert reverse == False

            if not filter_key:
                key = attrgetter("action_enabled")
            else:
                key = lambda x: filter_key(x) and attrgetter("action_enabled")(x)
            return ifilter(key, self.targets)

    def managed_targets(self, group_attr=None, group_key=None, filter_key=None, reverse=False):
        """Same method as enabled_targets() but filters also ExternalTarget."""
        if not filter_key:
            key = lambda x: not x.is_external()
        else:
            key = lambda x: filter_key(x) and not x.is_external()
        return self.enabled_targets(group_attr, group_key, key, reverse)

    def get_mgs_nids(self):
        return self.mgt.get_nids()
    
    def get_enabled_client_servers(self):
        return NodeSet.fromlist(imap(attrgetter("server"), self.enabled_clients()))

    def get_enabled_target_servers(self):
        return NodeSet.fromlist(imap(attrgetter("server"), self.enabled_targets()))

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
            action_class(nodes=distant_servers, fs=self, **kwargs).launch()
            task.resume()

    def install(self, fs_config_file, nodes=None, excluded=None):
        """
        Install FS config files, optionally on nodes `nodes', exluding nodes
        from `excluded'.

        Return the installed nodes (as a NodeSet).
        """
        servers = NodeSet()

        for target in self.targets:
            # install on failover partners too
            for s in target.servers:
                if not nodes or s in nodes:
                    servers.add(s)

        for client in self.clients:
            if not nodes or client.server in nodes:
                servers.add(client.server)

        # Do not install on excluded nodes
        if excluded:
           servers.difference_update(excluded)

        if servers:

            try:
                self._distant_action_by_server(Preinstall, servers)
                self._distant_action_by_server(Install, servers, config_file=fs_config_file)
            except ProxyActionError, e:
                # switch to public exception
                raise FSRemoteError(e.nodes, e.rc, e.message)
        
        return servers
        
    def remove(self):
        """
        Remove FS config files.
        """

        result = 0

        servers = NodeSet()

        self.proxy_errors = []

        # iterate over lustre servers
        for server, iter_targets in self.managed_targets(group_attr="server"):
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
            FSProxyAction(self, 'remove', servers, self.debug).launch()

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

    def format(self, **kwargs):

        # Remember format launched, so we can check their status once
        # all operations are done.
        format_launched = Set()

        self.proxy_errors = []

        for server, iter_targets in self.managed_targets(group_attr="server"):
            e_targets = list(iter_targets)

            if server.is_local():
                # local server
                for target in e_targets:
                    target.format(**kwargs)

            else:
                labels = NodeSet.fromlist([ t.label for t in e_targets ])
                FSProxyAction(self, 'format', NodeSet(server), self.debug,
                              labels=labels).launch()

            format_launched.update(e_targets)

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

        launched = Set()
        servers_statusall = NodeSet()
        self.proxy_errors = []

        # prepare servers status checks
        if flags & STATUS_SERVERS:
            for server, iter_targets in self.managed_targets(group_attr="server"):
                e_s_targets = list(iter_targets)
                if server.is_local():
                    for target in e_s_targets:
                        target.status()
                else:
                    labels = NodeSet.fromlist([ t.label for t in e_s_targets ])
                    FSProxyAction(self, 'status', NodeSet(server), self.debug,
                                  labels=labels).launch()

                launched.update(e_s_targets)

        # prepare clients status checks
        if flags & STATUS_CLIENTS:
            for client in self.enabled_clients():
                if client.server.is_local():
                    client.status()
                elif server not in servers_statusall:
                    servers_statusall.add(client.server)
                launched.add(client)

            # launch distant actions
            if len(servers_statusall) > 0:
                FSProxyAction(self, 'status', servers_statusall,
                              self.debug).launch()

        # run loop
        task_self().resume()
        
        # return a dict of {state : target list}
        rdict = {}

        # all launched targets+clients
        if self.proxy_errors:
            # find targets/clients affected by the runtime error(s)
            for target in launched:
                for nodes, msg in self.proxy_errors:
                    if target.server in nodes:
                        target.state = RUNTIME_ERROR

        for target in launched:
            # FIXME: in an ideal world, target.state shouldn't be None as the underlying
            # classes should have detected that case.
            if target.state == None:
                print "WARNING: no state report from target %s (%s)" % (target,
                        target.server)
                target.state = RUNTIME_ERROR
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
            FSProxyAction(self, 'status', NodeSet(server), self.debug,
                          target.type, RangeSet(str(target.index))).launch()

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

        result = 0

        # Iterate over targets, grouping them by target_order and server.
        for order, iter_targets in self.managed_targets(group_attr="target_order"):

            targets = sorted(iter_targets, key=attrgetter("server"))
            for server, iter_targets in groupby(targets, key=attrgetter("server")):
                targets = list(iter_targets)

                if server.is_local():
                    # Start targets if we are on the good server.
                    for target in targets:
                        # Note that target.start() should never block here:
                        # it will perform necessary non-blocking actions and
                        # (when needed) will start local ClusterShell workers.
                        target.start(**kwargs)
                else:
                    # Start per selected targets on this server.
                    labels = NodeSet.fromlist([ t.label for t in targets ])
                    FSProxyAction(self, 'start', NodeSet(server), self.debug,
                                  labels=labels).launch()

            # Resume current task, ie. start runloop, process workers events
            # and also act as a target-type barrier.
            task_self().resume()

            if self.proxy_errors:
                return RUNTIME_ERROR

            # Ok, workers have completed, perform late status check...
            for target in targets:
                if target.state > result:
                    result = target.state
                    if result > RECOVERING:
                        # Avoid broken cascading starts, so we break now if
                        # a target of the previous type failed to start.
                        return result

        return result


    def stop(self, **kwargs):
        """
        Stop file system.
        """
        rc = MOUNTED

        self.proxy_errors = []

        # We use a similar logic than start(): see start() for comments.
        # iterate over targets by target_order and server
        for order, iter_targets in self.managed_targets(group_attr="target_order", reverse=True):

            targets = sorted(iter_targets, key=attrgetter("server"))
            for server, iter_targets in groupby(targets, key=attrgetter("server")):
                targets = list(iter_targets)

                # iterate over lustre servers
                if server.is_local():
                    # Stop targets if we are on the good server.
                    for target in targets:
                        target.stop(**kwargs)
                else:
                    # Stop per selected targets on this server.
                    labels = NodeSet.fromlist([ t.label for t in targets ])
                    FSProxyAction(self, 'stop', NodeSet(server), self.debug,
                                  labels=labels).launch()

            task_self().resume()

            if self.proxy_errors:
                return RUNTIME_ERROR

            # Ok, workers have completed, perform late status check...
            for target in targets:
                if target.state > rc:
                    rc = target.state

        return rc

    def mount(self, **kwargs):
        """
        Mount FS clients.
        """
        servers_mountall = NodeSet()
        self.proxy_errors = []

        for client in self.enabled_clients():
            if client.server.is_local():
                # local client
                client.start(**kwargs)
            else:
                # distant client
                servers_mountall.add(client.server)

        if len(servers_mountall) > 0:
            FSProxyAction(self, 'mount', servers_mountall, self.debug).launch()

        task_self().resume()

        if self.proxy_errors:
            return RUNTIME_ERROR

        # Ok, workers have completed, perform late status check...
        for client in self.enabled_clients():
            if client.state is None:
                print "Unknown client.state after fs.mount() for %s" % client.server
                return RUNTIME_ERROR

        return client.state

    def umount(self, **kwargs):
        """
        Unmount FS clients.
        """
        servers_umountall = NodeSet()
        self.proxy_errors = []

        for client in self.enabled_clients():
            if client.server.is_local():
                # local client
                client.stop(**kwargs)
            else:
                # distant client
                servers_umountall.add(client.server)

        if len(servers_umountall) > 0:
            FSProxyAction(self, 'umount', servers_umountall, self.debug).launch()

        task_self().resume()

        if self.proxy_errors:
            return RUNTIME_ERROR

        # Ok, workers have completed, perform late status check...
        for client in self.enabled_clients():
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
        self.proxy_errors = []
        result = 0

        if Globals().get_tuning_file():
            # Install tuning.conf on enabled distant servers
            for server, iter_targets in self.managed_targets(group_attr="server"):
                if not server.is_local():
                    tune_all.add(server)
            # Add servers of enabled and distant clients
            tune_all.add(NodeSet.fromlist([ client.server for client in self.enabled_clients() if \
                not client.server.is_local() ]))

            if len(tune_all) > 0:
                self._distant_action_by_server(Install, tune_all, config_file=Globals().get_tuning_file())
                task.resume()
                tune_all.clear()

        # Apply tunings
        for server, iter_targets in self.managed_targets(group_attr="server"):
            e_targets = list(iter_targets)
            if server.is_local():
                types = Set()
                for t in e_targets:
                    types.add(type_map[t.type])

                rc = server.tune(tuning_model, types, self.fs_name)
                result = max(result, rc)
            else:
                labels = NodeSet.fromlist([ t.label for t in e_targets ])
                FSProxyAction(self, 'tune', NodeSet(server), self.debug,
                              labels=labels).launch()

        for client in self.enabled_clients():
            server = client.server
            if server.is_local():
                rc = server.tune(tuning_model, ['client'], self.fs_name)
                result = max(result, rc)
            elif server not in tune_all:
                tune_all.add(server)

        if len(tune_all) > 0:
            FSProxyAction(self, 'tune', tune_all, self.debug).launch()

        task.resume()

        if self.proxy_errors:
            return RUNTIME_ERROR

        return result

