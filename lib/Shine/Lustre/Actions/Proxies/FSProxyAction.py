# FSProxyAction.py -- Lustre generic FS proxy action class
# Copyright (C) 2009 CEA
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

from Shine.Lustre.Actions.Proxies.ProxyAction import ProxyAction, ProxyActionUnpackError
from Shine.Lustre.Component import INPROGRESS, RUNTIME_ERROR

from ClusterShell.NodeSet import NodeSet


class FSProxyAction(ProxyAction):
    """
    Generic file system command proxy action class.
    """

    def __init__(self, fs, action, nodes, debug, comps=None, addopts=None, 
                 failover=None):

        ProxyAction.__init__(self)
        self.fs = fs
        self.action = action
        assert isinstance(nodes, NodeSet)
        self.nodes = nodes
        self.debug = debug

        self._comps = comps

        self.addopts = addopts
        self.failover = failover

        if self.fs.debug:
            print "FSProxyAction %s on %s" % (action, nodes)

    def launch(self):
        """
        Launch FS proxy command.
        """
        command = ["%s" % self.progpath]
        command.append(self.action)
        command.append("-f %s" % self.fs.fs_name)
        command.append("-R")

        if self.debug:
            command.append("-d")

        if self._comps:
            labels = NodeSet.fromlist([ comp.label for comp in self._comps ])
            command.append("-l %s" % labels)

        if self.addopts:
            command.append("-o '%s'" % self.addopts)

        if self.failover:
            command.append("-F '%s'" % self.failover)

        # Schedule cluster command.
        self.task.shell(' '.join(command), nodes=self.nodes, handler=self)

    def ev_start(self, worker):
        """
        Proxy command is starting.
        """
        # Add a 'proxy' running action for each component.
        # XXX: This should be changed using a real event for proxy.
        if self._comps:
            for comp in self._comps:
                comp._add_action('proxy')

    def ev_read(self, worker):
        node, buf = worker.last_read()
        try:
            event, params = self._shine_msg_unpack(buf)
            self.fs._handle_shine_event(event, node, **params)
        except ProxyActionUnpackError, e:
            # ignore any non shine messages
            pass

    def ev_close(self, worker):
        """
        End of proxy command.
        """

        # Remove the 'proxy' running action for each component.
        if self._comps:
            for comp in self._comps:
                # XXX: This should be changed using a real event for proxy.
                comp._del_action('proxy')

                # At this step, there should be no more INPROGRESS component.
                # If yes, this is a bug, change state to RUNTIME_ERROR.
                # INPROGRESS management could be change using running action
                # list.
                if comp.state == INPROGRESS:
                    if len(comp._list_action()):
                        actions = "actions: " + ", ".join(comp._list_action())
                    print "ERROR: bad state for %s: %d %s" % \
                                    (comp.label, comp.state, actions)
                    comp.state = RUNTIME_ERROR

        # Gather nodes by return code
        for rc, nodes in worker.iter_retcodes():
            # some common remote errors:
            # rc 127 = command not found
            # rc 126 = found but not executable
            # rc 1 = python failure...
            if rc != 0:

                # Built the list of nodes without output
                nobuffer_nodes = nodes

                # Gather these nodes by buffer
                for buffer, nodes in worker.iter_buffers(nodes):

                    # Ok, those nodes have output, forget them
                    nobuffer_nodes.difference_update(nodes)

                    ### FIXME #25: temporary SHINE msg filter to avoid pickle 
                    ### data to be dumped on screen. To be fixed as soon as
                    ### ClusterShell is able to clean MsgTree buffers on demand
                    ### (CS trac #3).
                    buf = ""
                    for line in buffer.splitlines():
                        if not line.startswith("SHINE:"):
                            buf += "%s\n" % line 

                    # Handle proxy command error which rc >= 127 and 
                    self.fs._handle_shine_proxy_error(nodes, "Remote action %s failed: %s" % \
                            (self.action, buf))

                # Raise an error for nodes without outputs
                if len(nobuffer_nodes) > 0:
                    self.fs._handle_shine_proxy_error(nobuffer_nodes, \
                        "Remote action %s failed: No response" % (self.action))
