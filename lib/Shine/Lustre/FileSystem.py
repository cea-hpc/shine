# FileSystem.py -- Lustre FS
# Copyright (C) 2007-2015 CEA
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

"""
Lustre FileSystem class.

Represents a Lustre FS.
"""

from __future__ import print_function

import os
import sys
import socket
import logging
import logging.handlers

from ClusterShell.MsgTree import MsgTree
from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import task_self

from Shine.Configuration.Globals import Globals

from Shine.Lustre.Actions.Action import ActionGroup, ACT_ERROR
from Shine.Lustre.Actions.Proxy import FSProxyAction
from Shine.Lustre.Actions.Install import Install

from Shine.Lustre.EventHandler import EventHandler
from Shine.Lustre.Component import ComponentGroup
from Shine.Lustre.Server import Server
from Shine.Lustre.Client import Client
from Shine.Lustre.Router import Router
from Shine.Lustre.Target import MGT, MDT, OST, Journal
# FileSystem class needs to re-export all Target status, they are used in
# Shine.Commands.*
from Shine.Lustre.Component import INPROGRESS, EXTERNAL, MOUNTED, \
                                   RECOVERING, OFFLINE, RUNTIME_ERROR, \
                                   CLIENT_ERROR, TARGET_ERROR, MIGRATED, \
                                   NO_DEVICE


class FSError(Exception):
    """
    Base FileSystem error exception.
    """

class FSRemoteError(FSError):
    """
    Remote host(s) not available, or a remote operation failed.
    """
    def __init__(self, nodes, rc, msg):
        FSError.__init__(self)
        self.msg = msg
        self.nodes = nodes
        self.rc = int(rc)

    def __str__(self):
        return "%s: %s [rc=%d]" % (self.nodes, self.msg, self.rc)


class FileSystem:
    """
    The Lustre FileSystem abstract class.
    """

    def __init__(self, fs_name, event_handler=None):
        self.fs_name = fs_name
        self.hdlr = event_handler or EventHandler()
        self.proxy_errors = MsgTree()

        # All FS components (MGT, MDT, OST, Clients, ...)
        self.components = ComponentGroup()

        # file system MGT
        self.mgt = None

        # Local server reference
        self.local_server = None

        self.debug = False
        self.logger = self._setup_logging()

    def set_debug(self, debug):
        self.debug = debug

    def _setup_logging(self):
        """Setup logging configuration for the whole filesystem."""
        # XXX: This is only here for fsck, currently.

        logger = logging.getLogger('Shine.Lustre')

        # Level
        if self.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        if logger.handlers:
            # If some handlers already exist, the logger singleton is already
            # configured, so just return it to avoid duplicate handlers.
            return logger

        # Formatter
        formatter = logging.Formatter(datefmt="%Y-%m-%d %X",
                      fmt='%(name)s %(levelname)s  %(message)s')

        try:
            # Handler
            handler = logging.handlers.SysLogHandler(address='/dev/log')
            logger.addHandler(handler)
            handler.setFormatter(formatter)
        except socket.error:
            logging.raiseExceptions = False
            msg = "Error connecting to syslog, disabling logging."
            print("WARNING: %s" % msg, file=sys.stderr)

        return logger


    def get_mgs_nids(self):
        return self.mgt.get_nids()

    #
    # file system event handling
    #

    def local_event(self, evtype, **params):
        # Currently, all event callbacks need a node.
        # When localy called, add the current node
        self.hdlr.local_event(evtype, **params)

    def distant_event(self, evtype, node, **params):

        # Update the local component instance with the provided instance
        # if one is available in params.
        if evtype == 'comp':
            other = params['info'].elem
            other.fs = self
            try:
                # Special hack for Journal object as they are not put in
                # components list.
                if other.TYPE == Journal.TYPE:
                    other.target.fs = self
                    target = self.components[other.target.uniqueid()]
                    target.journal.update(other)
                    comp = target.journal
                else:
                    comp = self.components[other.uniqueid()]
                    # comp.update() updates the component state
                    # and disk information if the component is a target.
                    # These information don't need to be updated unless
                    # we are on a completion event.
                    if params['status'] not in ('start', 'progress'):
                        # ensure other.server is the actual distant server
                        other.server = comp.allservers().select(
                                                            NodeSet(node))[0]

                        # update target from remote one
                        comp.update(other)

                # substitute target parameter by local one
                params['comp'] = comp
            except KeyError as error:
                print("ERROR: Component update failed (%s)" % str(error),
                      file=sys.stderr)

        self.hdlr.event_callback(evtype, node=node, **params)

    def _handle_shine_proxy_error(self, nodes, message):
        """
        Store error messages, for later processing.

        Hostnames are replaced by 'THIS_SHINE_HOST' to allow message grouping.
        Grouping outputs which only differ by the host name.
        """
        message = message.replace(str(nodes).encode(), b'THIS_SHINE_HOST')
        self.proxy_errors.add(str(nodes), message)

    #
    # file system construction
    #

    def _attach_component(self, comp):
        if comp.TYPE == MGT.TYPE:
            if self.mgt and len(self.mgt.get_nids()) > 0:
                raise FSError("A Lustre filesystem has only one MGT.")
            self.mgt = comp
        self.components.add(comp)

    def new_target(self, server, type, index, dev, jdev=None, group=None,
                   tag=None, enabled=True, mode='managed', network=None,
                   active='yes', dev_run_action=None):
        """
        Create a new attached target.
        """
        TYPE_CLASSES = {MGT.TYPE: MGT, MDT.TYPE: MDT, OST.TYPE: OST}
        if type not in TYPE_CLASSES:
            raise FSError("Unrecognized target type \"%s\"" % type)

        target = TYPE_CLASSES[type](fs=self, server=server, index=index,
                                    dev=dev, jdev=jdev, group=group, tag=tag,
                                    enabled=enabled, mode=mode, network=network,
                                    active=active,
                                    dev_run_action=dev_run_action)
        self._attach_component(target)
        return target

    def new_client(self, server, mount_path, mount_options=None, subdir=None,
                   enabled=True):
        """
        Create a new attached client.
        """
        client = Client(self, server, mount_path, mount_options, subdir,
                        enabled)
        self._attach_component(client)
        return client

    def new_router(self, server, enabled=True):
        """
        Create a new attached router.
        """
        router = Router(self, server, enabled)
        self._attach_component(router)
        return router

    #
    # Task management.
    #

    def _proxy_action(self, action, servers, comps=None, **kwargs):
        """Create a proxy action to remotely run a shine action."""
        assert isinstance(servers, NodeSet)
        assert comps is None or isinstance(comps, ComponentGroup)
        return FSProxyAction(self, action, servers, self.debug, comps, **kwargs)

    def _run_actions(self):
        """
        Start actions run-loop.

        It clears all previous proxy errors and starts task run-loop. This
        launches all FSProxyAction prepared before by example.
        """
        self.proxy_errors = MsgTree()
        task_self().set_default("stderr_msgtree", False)
        task_self().set_info('connect_timeout', 
                             Globals().get_ssh_connect_timeout())
        task_self().resume()

    def _check_errors(self, expected_states, components=None, actions=None):
        """
        This verifies that executed tasks were successfull.

        It verifies all provided components (Target, Clients, ...) have
        expected state. If not, it returns the most incoherent state.

        If there is no error, it returns the expected state.
        """
        assert isinstance(expected_states, list)
        result = set()

        if actions and actions.status() == ACT_ERROR:
            result.add(TARGET_ERROR)

        # If a component list is provided, check that all components from it
        # have expected state.
        for comp in components or []:

            # This should never happen but it is convenient for debugging if
            # there is some uncatched bug somewhere.
            # (ie: cannot unpickle due to ClusterShell version mismatch)
            if comp.state is None:
                msg = "WARNING: no state report from node %s" % comp.server
                print(msg, file=sys.stderr)
                comp.state = RUNTIME_ERROR

            if comp.state not in expected_states:
                result.add(comp.state)

            # Compute component's server.
            # Although not the best place semantically speaking to perform this
            # task, update_server() is meaningful only when all the component
            # states have been filled, and here, we are sure it is the case.
            # So, waiting for a better solution, _check_errors() is the
            # best place to compute the component server.
            if comp.update_server() is False:
                msg = "WARNING: %s is mounted multiple times" % comp.label
                self._handle_shine_proxy_error(str(comp.server.hostname), msg.encode())

        # if empty set, add expected_states[0]
        if not result:
            result.add(expected_states[0])

        return result

    def _distant_action_by_server(self, action_class, servers, **kwargs):

        # filter local server
        distant_servers = Server.distant_servers(servers)

        # perform action on distant servers
        if len(distant_servers) > 0:
            action = action_class(nodes=distant_servers, fs=self, **kwargs)
            action.launch()
            self._run_actions()

            if action.status() == ACT_ERROR:
                err_code = None
                if task_self().num_timeout():
                    err_code = -1
                elif task_self().max_retcode():
                    err_code = task_self().max_retcode()

                # FSRemoteError is limited and cannot handle more than 1 error
                msg, nodes = list(self.proxy_errors.walk())[0]
                nodes = NodeSet.fromlist(nodes)
                msg = msg.message().decode().replace('THIS_SHINE_HOST',
                                                     str(nodes))
                raise FSRemoteError(nodes, err_code, msg)

    def install(self, fs_config_file, servers=None, **kwargs):
        """
        Install filesystem configuration file on its servers. 
        Server list is built from enabled targets and enabled clients only.
        """

        # Get all possible servers
        servers = (servers or self.components.managed().allservers())

        self._distant_action_by_server(Install, servers,
                                       config_file=fs_config_file, **kwargs)

    def remove(self, servers=None, **kwargs):
        """
        Remove FS config files.
        """
        result = 0

        if servers is None:
            # Get all possible servers 
            servers = self.components.managed().allservers()

        # filter local server
        distant_servers = Server.distant_servers(servers)

        # If size is different, we have a local server in the list
        if len(distant_servers) < len(servers):
            # remove local fs configuration file
            fs_file = os.path.join(Globals().get_conf_dir(),
                                   "%s.xmf" % self.fs_name)
            if os.path.exists(fs_file):
                self.hdlr.log('detail', msg='[DEL] %s' % fs_file)
                if kwargs.get('dryrun', False):
                    result = 0
                else:
                    result = os.remove(fs_file)

        if len(distant_servers) > 0:
            # Perform the remove operations on all targets for these nodes.
            self._proxy_action('remove', distant_servers, **kwargs).launch()

        # Run local actions and FSProxyAction
        self._run_actions()

        if len(self.proxy_errors) > 0:
            return RUNTIME_ERROR

        return result

    def _prepare(self, action, comps=None, groupby=None, reverse=False,
                 need_unload=False, tunings=None, allservers=False, **kwargs):
        """
        Instanciate all actions for the component list and but them in a graph
        of ActionGroup().

        Action could be local or proxy actions.
        Components list is filtered, based on action name.
        """

        graph = ActionGroup()

        comps = comps or self.components

        first_comps = None
        last_comps = None
        localsrv = None
        modules = list()
        localcomps = None

        if groupby:
            iterable = comps.groupby(attr=groupby, reverse=reverse)
        else:
            iterable = [(None, comps)]

        # Iterate over targets, grouping them by start order and server.
        for _order, comps in iterable:

            graph.add(ActionGroup())
            compgrp = ActionGroup()
            proxygrp = ActionGroup()

            for srv, comps in comps.groupbyserver(allservers=allservers):
                if srv.action_enabled is True:
                    if srv.is_local():
                        localsrv = srv
                        localcomps = comps
                        for comp in comps:
                            compgrp.add(getattr(comp, action)(**kwargs))
                    else:
                        act = self._proxy_action(action, srv.hostname,
                                                 comps=comps,
                                                 need_unload=need_unload,
                                                 **kwargs)
                        if tunings and tunings.filename:
                            copy = Install(srv.hostname, self, tunings.filename,
                                           comps=comps, **kwargs)
                            act.depends_on(copy)
                            proxygrp.add(copy)
                        proxygrp.add(act)

            if len(compgrp) > 0:
                graph[-1].add(compgrp)
                # Keep track of first comp group
                if first_comps is None:
                    first_comps = compgrp
                    first_comps.parent = graph[-1]
                # Keep track of last comp group
                last_comps = compgrp
                last_comps.parent = graph[-1]

                # Build module loading list, if needed
                for comp_action in compgrp:
                    modules.extend(module
                                   for module in comp_action.needed_modules()
                                   if module not in modules)

            if len(proxygrp) > 0:
                graph[-1].add(proxygrp)


        # Add module loading, if needed.
        if first_comps is not None and len(modules) > 0:
            modgrp = ActionGroup()
            for module in modules:
                modgrp.add(localsrv.load_modules(modname=module, **kwargs))

            # Serialize modules loading actions
            modgrp.sequential()

            first_comps.parent.add(modgrp)
            first_comps.depends_on(modgrp)

        # Apply tuning to last component group, if needed
        if tunings is not None and last_comps is not None:
            tune = localsrv.tune(tunings, localcomps, self.fs_name, **kwargs)
            last_comps.parent.add(tune)
            tune.depends_on(last_comps)

        # Add module unloading to last component group, if needed.
        if need_unload and last_comps is not None:
            unload = localsrv.unload_modules(**kwargs)
            last_comps.parent.add(unload)
            unload.depends_on(last_comps)

        # Join the different part together
        graph.sequential()

        return graph


    def format(self, comps=None, **kwargs):
        """Format filesystem targets."""
        comps = (comps or self.components).managed(supports='format')
        actions = self._prepare('format', comps, **kwargs)
        actions.launch()
        self._run_actions()

        # Check for errors and return OFFLINE or error code
        return self._check_errors([OFFLINE], comps, actions)


    def tunefs(self, comps=None, **kwargs):
        """Modify component option set at format."""
        comps = (comps or self.components).managed(supports='tunefs')
        actions = self._prepare('tunefs', comps, **kwargs)
        actions.launch()
        self._run_actions()

        # Check for errors and return OFFLINE or error code
        return self._check_errors([OFFLINE], comps, actions)


    def fsck(self, comps=None, **kwargs):
        """Check component filesystem coherency."""
        comps = (comps or self.components).managed(supports='fsck')
        actions = self._prepare('fsck', comps, **kwargs)
        actions.launch()
        self._run_actions()
        # Check for errors and return OFFLINE or error code
        return self._check_errors([OFFLINE], comps, actions)


    def status(self, comps=None, allservers=True, **kwargs):
        """Get status of filesystem."""
        comps = (comps or self.components).managed(supports='status')
        actions = self._prepare('status', comps, allservers=allservers,
                                **kwargs)
        actions.launch()
        self._run_actions()

        # Here we check MOUNTED but in fact, any status is OK.
        return self._check_errors([MOUNTED], comps)

    def start(self, comps=None, **kwargs):
        """Start Lustre file system servers."""
        comps = (comps or self.components).managed(supports='start')

        actions = self._prepare('start', comps, groupby='START_ORDER', **kwargs)
        actions.launch()
        self._run_actions()

        return self._check_errors([MOUNTED, RECOVERING], comps, actions)

    def stop(self, comps=None, need_unload=True, **kwargs):
        """Stop file system."""
        comps = (comps or self.components).managed(supports='stop')
        actions = self._prepare('stop', comps, groupby='START_ORDER',
                                reverse=True, need_unload=need_unload,
                                **kwargs)
        actions.launch()
        self._run_actions()

        return self._check_errors([OFFLINE], comps)

    def mount(self, comps=None, **kwargs):
        """Mount FS clients."""
        comps = (comps or self.components).managed(supports='mount')
        actions = self._prepare('mount', comps, **kwargs)
        actions.launch()
        self._run_actions()

        # Ok, workers have completed, perform late status check...
        return self._check_errors([MOUNTED], comps, actions)

    def umount(self, comps=None, need_unload=True, **kwargs):
        """Unmount FS clients."""
        comps = (comps or self.components).managed(supports='umount')
        actions = self._prepare('umount', comps, need_unload=need_unload,
                                **kwargs)
        actions.launch()
        self._run_actions()

        # Ok, workers have completed, perform late status check...
        return self._check_errors([OFFLINE], comps)

    def execute(self, comps=None, **kwargs):
        """Execute custom command."""
        comps = (comps or self.components).managed(supports='execute')
        actions = self._prepare('execute', comps, **kwargs)
        actions.launch()
        self._run_actions()

        # Here we check MOUNTED but in fact, any status is OK.
        # XXX: Is that ok, to check MOUNTED here?
        return self._check_errors([MOUNTED], comps, actions)

    def tune(self, tuning_model, comps=None, **kwargs):
        """Tune server."""
        comps = (comps or self.components).managed()

        actions = ActionGroup()
        for server, srvcomps in comps.groupbyserver():
            if server.is_local():
                actions.add(server.tune(tuning_model, srvcomps, self.fs_name,
                                        **kwargs))
            else:
                act = self._proxy_action('tune', server.hostname, srvcomps,
                                         **kwargs)
                if tuning_model.filename:
                    copy = Install(server.hostname, self, tuning_model.filename,
                                   comps=srvcomps, **kwargs)
                    act.depends_on(copy)
                    actions.add(copy)

                actions.add(act)

        # Run local actions and FSProxyAction
        actions.launch()
        self._run_actions()

        # Check actions status and return MOUNTED if no error
        return self._check_errors([MOUNTED], None, actions)
