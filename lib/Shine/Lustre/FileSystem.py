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

from sets import Set
import socket
import os
import sys

from itertools import ifilter, imap, groupby
from operator import attrgetter

from ClusterShell.NodeSet import NodeSet, RangeSet
from ClusterShell.Task import task_self

from Shine.Configuration.Globals import Globals

from Shine.Lustre.Actions.Action import ActionFailedError
from Shine.Lustre.Actions.Proxies.ProxyAction import ProxyActionError
from Shine.Lustre.Actions.Proxies.FSProxyAction import FSProxyAction
from Shine.Lustre.Actions.Install import Install
from Shine.Lustre.Actions.Proxies.Preinstall import Preinstall

from Shine.Lustre.Client import Client
from Shine.Lustre.Target import MGT, MDT, OST
# FileSystem class needs to re-export all Target status, they are used in Shine.Commands.*
from Shine.Lustre.Component import INPROGRESS, EXTERNAL, MOUNTED, RECOVERING, OFFLINE, RUNTIME_ERROR, CLIENT_ERROR, TARGET_ERROR


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

        # All FS components (MGT, MDT, OST, Clients, ...)
        self._components = []

        # file system MGT
        self.mgt = None

    def set_debug(self, debug):
        self.debug = debug

    def get_mgs_nids(self):
        return self.mgt.get_nids()
    
    #
    # file system event handling
    #

    def _invoke(self, event, **kwargs):
        if self.event_handler:
            if 'target' in kwargs or 'client' in kwargs:
                kwargs.setdefault('node', None)
            getattr(self.event_handler, event)(**kwargs)

    def set_eventhandler(self, event_handler):
        self.event_handler = event_handler

    def _handle_shine_event(self, event, node, **params):
        
        # We should have a target or a client, not both
        comp = params.get('target')
        name = 'target'
        if not comp:
            comp = params.get('client')
            name = 'client'
        else:
            assert(not params.get('client'))

        if comp:
            found = False
            for any in self._components:
                if any.match(comp):
                    # update target from remote one
                    any.update(comp)
                    # substitute target parameter by local one
                    params[name] = any
                    found = True
            if not found:
                print "ERROR: Component update failed (%s)" % comp

        self._invoke(event, node=node, **params)

    def _handle_shine_proxy_error(self, nodes, message):
        self.proxy_errors.append((NodeSet(nodes), message))

    #
    # file system construction
    #

    def _attach_component(self, comp):
        self._components.append(comp)
        if comp.TYPE == MGT.TYPE:
            self.mgt = comp

    def new_target(self, server, type, index, dev, jdev=None, group=None,
                   tag=None, enabled=True, mode='managed'):
        """
        Create a new attached target.
        """
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
        return Client(self, server, mount_path, enabled)

    #
    # Iterators over filesystem components
    #

    def enabled_components(self, group_attr=None, group_key=None, supports=None,
                           filter_key=None, reverse=False):
        """This function returns an iterator over enabled components with 3 
        additionnal possibilities:
        - Filter them more precisely (using filter_key)
        - Group results by attributes or key (using group_attr or group_key)
        - Reverse results (using reverse)
        All can be combined.

        Example #1: Iterate over enabled OSTs only:
         self.enabled_components(filter_key=lambda t: t.TYPE == OST.TYPE)

        Example #2: Group component by server
         self.enabled_components(group_attr="server")

        Example #3: Group using 2 criterias, first type and then server
         key = lambda t: (t.TYPE, t.server)
         self.enabled_components(group_key=key)
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
            sortlist = sorted(self.enabled_components(filter_key=filter_key, supports=supports), \
                              key=group_key, reverse=reverse)
            return groupby(sortlist, group_key)
        else:
            # As we do not group and sort, reverse has no meaning here
            assert reverse == False

            if not filter_key and not supports:
                key = attrgetter("action_enabled")
            elif not filter_key and supports:
                key = lambda x: x.capable(supports)
            elif filter_key and supports:
                key = lambda x: filter_key(x) and x.capable(supports) and attrgetter("action_enabled")(x)
            else:
                key = lambda x: filter_key(x) and attrgetter("action_enabled")(x)
            return ifilter(key, self._components)

    def managed_components(self, group_attr=None, group_key=None, supports=None, filter_key=None, reverse=False):
        """Same method as enabled_components() but filters also external components."""
        if not filter_key:
            key = lambda x: not x.is_external()
        else:
            key = lambda x: filter_key(x) and not x.is_external()
        return self.enabled_components(group_attr, group_key, supports, key, reverse)

    def managed_component_servers(self, supports=None, filter_key=None):
        return NodeSet.fromlist(imap(attrgetter("server"), \
                                self.managed_components(supports=supports, \
                                                       filter_key=filter_key)))

    def disable_clients(self):
        """
        Change all client components to disabled mode.
        Warning, this is a temporary method which will change when a 
        better solution will be available.
        """
        key = lambda c: c.TYPE == Client.TYPE
        for comp in self.managed_components(filter_key=key):
            comp.action_enabled = False

    #
    # Task management.
    #

    def _run_actions(self):
        """
        Start actions run-loop.

        It clears all previous proxy errors and starts task run-loop. This
        launches all FSProxyAction prepared before by example.
        """
        self.proxy_errors = []
        # XXX: Warning, also update _distant_action_by_server()
        task_self().set_info('connect_timeout', Globals().get_ssh_connect_timeout())
        task_self().resume()

    def _check_errors(self, expected_states, components=None):
        """
        This verifies that executed tasks were successfull.

        It checks no proxy error have been reported.
        It verifies all provided components (Target, Clients, ...) have
        expected state. If not, it returns the most incoherent state.

        If there is no error, it returns the expected state.
        """
        assert type(expected_states) is list

        # Proxy commands should not have return errors
        if self.proxy_errors:

            # Find targets/clients affected by the runtime error(s)
            if components:
                error_nodes = NodeSet.fromlist([ n for n, e in self.proxy_errors])
                for comp in components:
                    # This target/client has no defined state and is on an
                    # error node, so we consider there was an error
                    if comp.server in error_nodes and comp.state is None:
                        comp.state = RUNTIME_ERROR

        # If a component list is provided, check that all components from it
        # have expected state.
        result = 0
        if components:
            for comp in components:

                # Workaround bug when state is None (Trac ticket #11)
                # Bug is now closed, maybe this could be removed?
                if comp.state is None:
                    print "WARNING: no state report from node %s" % comp.server
                    comp.state = RUNTIME_ERROR

                if comp.state not in expected_states:
                    result = max(result, comp.state)

            if result:
                return result

        return expected_states[0]

    def _distant_action_by_server(self, action_class, servers, **kwargs):

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
            # XXX: merge with _run_actions()
            task_self().set_info('connect_timeout', Globals().get_ssh_connect_timeout())
            task_self().resume()

    def install(self, fs_config_file):
        """
        Install filesystem configuration file on its servers. 
        Server list is built from enabled targets and enabled clients only.
        """

        servers = self.managed_component_servers()

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

        # iterate over lustre servers
        for server, iter_comps in self.managed_components(group_attr="server"):
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

        # Run local actions and FSProxyAction
        self._run_actions()

        if self.proxy_errors:
            return RUNTIME_ERROR
        
        return result

    def format(self, **kwargs):

        # Remember format launched, so we can check their status once
        # all operations are done.
        format_launched = Set()

        for server, iter_targets in self.managed_components(group_attr="server", supports='format'):
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

        # Run local actions and FSProxyAction
        self._run_actions()

        # Check for errors and return OFFLINE or error code
        return self._check_errors([OFFLINE], format_launched)

    def status(self, flags=STATUS_ANY):
        """
        Get status of filesystem.
        """

        launched = Set()

        # Filter components depending on flags
        key = lambda c: ((flags & STATUS_SERVERS) and hasattr(c, 'index')) or \
                        ((flags & STATUS_CLIENTS) and c.TYPE == Client.TYPE)

        for server, iter_comps in self.managed_components(group_attr="server", supports='status', filter_key=key):
            e_s_comps = list(iter_comps)
            if server.is_local():
                for comp in e_s_comps:
                    comp.status()
            else:
                labels = NodeSet.fromlist([ c.label for c in e_s_comps ])
                FSProxyAction(self, 'status', NodeSet(server), self.debug,
                              labels=labels).launch()

            launched.update(e_s_comps)

        # Run local actions and FSProxyAction
        self._run_actions()
        
        # Here we check MOUNTED but in fact, any status is OK.
        return self._check_errors([MOUNTED], launched)

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
                          target.TYPE, RangeSet(str(target.index))).launch()

        task_self().resume()

        # XXX: No error check?

    def start(self, **kwargs):
        """
        Start Lustre file system servers.
        """

        # What starting order to use?
        key = lambda t: t.TYPE == MDT.TYPE
        for target in self.managed_components(filter_key=key):
            # Found enabled MDT: perform writeconf check.
            self.status_target(target)
            if target.has_first_time_flag() or target.has_writeconf_flag():
                # first_time or writeconf flag found, start MDT before OSTs
                MDT.START_ORDER, OST.START_ORDER = OST.START_ORDER, MDT.START_ORDER

        # Iterate over targets, grouping them by start order and server.
        for order, iter_targets in self.managed_components(group_attr="START_ORDER", supports='start'):

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
            self._run_actions()

            # Avoid broken cascading starts, so we break now if
            # a target of the previous type failed to start.
            result = self._check_errors([MOUNTED, RECOVERING], targets)
            if result not in [MOUNTED, RECOVERING]:
                return result

        return MOUNTED


    def stop(self, **kwargs):
        """
        Stop file system.
        """

        # We use a similar logic than start(): see start() for comments.
        # iterate over targets by start order and server
        for order, iter_targets in self.managed_components(group_attr="START_ORDER", supports='stop', reverse=True):

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

            # Run local actions and FSProxyAction
            self._run_actions()
        
            result = self._check_errors([OFFLINE], targets)
            if result != OFFLINE:
                return result

        return OFFLINE

    def mount(self, **kwargs):
        """
        Mount FS clients.
        """
        servers_mountall = NodeSet()

        for client in self.managed_components(supports='mount'):
            if client.server.is_local():
                # local client
                client.mount(**kwargs)
            else:
                # distant client
                servers_mountall.add(client.server)

        if len(servers_mountall) > 0:
            FSProxyAction(self, 'mount', servers_mountall, self.debug).launch()

        # Run local actions and FSProxyAction
        self._run_actions()

        # Ok, workers have completed, perform late status check...
        return self._check_errors([MOUNTED], self.managed_components(supports='mount'))

    def umount(self, **kwargs):
        """
        Unmount FS clients.
        """
        servers_umountall = NodeSet()

        for client in self.managed_components(supports='umount'):
            if client.server.is_local():
                # local client
                client.umount(**kwargs)
            else:
                # distant client
                servers_umountall.add(client.server)

        if len(servers_umountall) > 0:
            FSProxyAction(self, 'umount', servers_umountall, self.debug).launch()

        # Run local actions and FSProxyAction
        self._run_actions()

        # Ok, workers have completed, perform late status check...
        return self._check_errors([OFFLINE], self.managed_components(supports='umount'))

    def info(self):
        pass

    def tune(self, tuning_model):
        """
        Tune server.
        """
        task = task_self()
        tune_all = NodeSet()
        type_map = { 'mgt': 'mgs', 'mdt': 'mds', 'ost' : 'oss', 'client': 'client' }

        if Globals().get_tuning_file():
            # Install tuning.conf on enabled distant servers
            for server, iter_comp in self.managed_components(group_attr="server"):
                if not server.is_local():
                    tune_all.add(server)

            if len(tune_all) > 0:
                try:
                    self._distant_action_by_server(Install, tune_all, config_file=Globals().get_tuning_file())
                except ActionFailedError, error:
                    print "WARNING: %s" % str(error)

        # Apply tunings
        for server, iter_comp in self.managed_components(group_attr="server", supports='label'):
            e_comps = list(iter_comp)
            if server.is_local():
                types = Set()
                for t in e_comps:
                    types.add(type_map[t.TYPE])

                server.tune(tuning_model, types, self.fs_name)
            else:
                labels = NodeSet.fromlist([ t.label for t in e_comps ])
                FSProxyAction(self, 'tune', NodeSet(server), self.debug,
                              labels=labels).launch()

        # Run local actions and FSProxyAction
        self._run_actions()

        # Check for proxy errors, and return 'result' if no proxy errors
        result = task_self().max_retcode()
        return self._check_errors([result])
