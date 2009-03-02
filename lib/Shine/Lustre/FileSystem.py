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

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

from EventHandler import *
from Target import *
from Server import *

import Actions.Proxies.Start

# Action exceptions
from Actions.Action import ActionErrorException
from Actions.Proxies.ProxyAction import ProxyActionError

from Actions.Install import Install
from Actions.Proxies.Preinstall import Preinstall
from Actions.Proxies.FSProxyAction import FSProxyAction

from ClusterShell.NodeSet import NodeSet, RangeSet

import copy
import socket


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
        return "%s: %s [%d]" % (self.nodes, self.message, self.rc)


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
        if 'target' in kwargs:
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
                    # substitute target parameter
                    params['target'] = target
                    found = True
            if not found:
                print "Target Update FAILED (%s)" % target

        self._invoke(event, node=node, **params)

    #
    # file system construction
    #

    def _attach_target(self, target):
        self.targets.append(target)
        if target.type == 'mgt':
            self.mgt = target
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

    def get_mgs_nids(self):
        return self.mgt.get_nids()

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

    def install(self, fs_config_file):
        """
        """
        servers = NodeSet()

        for target in self.targets:
            # install on failover partners too
            for s in target.servers:
                servers.add(s)

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

    def _iter_targets_by_type(self, reverse=False):
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
    
    def status(self):

        for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():
            if len(e_s_targets) == 0:
                continue

            if server.is_local():
                for target in e_s_targets:
                    target.status()
            else:
                assert False

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
        Start file system.
        """
        servers_startall = NodeSet()

        # What starting order?
        for target in self.targets:
            if isinstance(target, MDT) and target.action_enabled:
                # Found enabled MDT. Perform writeconf check.
                self.status_target(target)
                if target.has_first_time_flag() or target.has_writeconf_flag():
                    MDT.target_order = 2
                    print "WRITECONF!!"
                    break

        self.targets.sort()

        #print "0:"
        for type, (a_targets, e_targets) in self._iter_targets_by_type():
            #print "1:", type, a_targets, e_targets
            
            for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():
                #print "2:", server, e_s_targets

                type_e_targets = e_targets.intersection(e_s_targets)
                if len(type_e_targets) == 0:
                    # skip as no target of this type is enabled on this server
                    continue

                if server.is_local():
                    for target in type_e_targets:
                        target.start(**kwargs)
                else:
                    # distant server: check if all server targets have been selected
                    assert a_s_targets.issuperset(type_e_targets)
                    assert len(type_e_targets) > 0

                    if len(type_e_targets) == len(a_s_targets):
                        # "start all targets on this server" detected
                        servers_startall.add(server)
                    else:
                        # start per selected targets on this server
                        for t_type, t_rangeset in \
                                self._iter_type_idx_for_targets(type_e_targets):
                            action = FSProxyAction(self, 'start',
                                    NodeSet(server), self.debug, t_type, t_rangeset)
                            action.launch()

            if len(servers_startall) > 0:
                action = FSProxyAction(self, 'start', servers_startall, self.debug)
                action.launch()

            # Resume current task, ie. perform the job now and act as
            # a target-type barrier.
            try:
                task_self().resume()
            except ProxyActionError, e:
                # switch to public exception
                raise FSRemoteError(e.nodes, e.rc, e.message)
            
            servers_startall.clear()

    def stop(self, **kwargs):
        """
        Stop file system.
        """
        servers_stopall = NodeSet()

        self.targets.sort()
        self.targets.reverse()

        #print "0:"
        for type, (a_targets, e_targets) in self._iter_targets_by_type():
            #print "1:", type, a_targets, e_targets
            
            for server, (a_s_targets, e_s_targets) in self._iter_targets_by_server():
                #print "2:", server, e_s_targets

                type_e_targets = e_targets.intersection(e_s_targets)
                if len(type_e_targets) == 0:
                    # skip as no target of this type is enabled on this server
                    continue

                if server.is_local():
                    for target in type_e_targets:
                        target.stop(**kwargs)
                else:
                    # distant server: check if all server targets have been selected
                    assert a_s_targets.issuperset(type_e_targets)
                    assert len(type_e_targets) > 0

                    if len(type_e_targets) == len(a_s_targets):
                        # "stop all targets on this server" detected
                        servers_stopall.add(server)
                    else:
                        # stop per selected targets on this server
                        for t_type, t_rangeset in \
                                self._iter_type_idx_for_targets(type_e_targets):
                            action = FSProxyAction(self, 'stop',
                                    NodeSet(server), self.debug, t_type, t_rangeset)
                            action.launch()

            if len(servers_stopall) > 0:
                action = FSProxyAction(self, 'stop', servers_stopall, self.debug)
                action.launch()

            # Resume current task, ie. perform the job now and act as
            # a target-type barrier.
            try:
                task_self().resume()
            except ProxyActionError, e:
                # switch to public exception
                raise FSRemoteError(e.nodes, e.rc, e.message)
            
            servers_stopall.clear()


    def info(self):
        pass

