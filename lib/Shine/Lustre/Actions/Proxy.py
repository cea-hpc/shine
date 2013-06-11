# Proxy.py -- Lustre generic FS proxy action class
# Copyright (C) 2009-2013 CEA
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

import os
import sys
import binascii, pickle

from ClusterShell.Task import task_self
from Shine.Lustre.Component import INPROGRESS, RUNTIME_ERROR
from Shine.Lustre.Actions.Action import Action

# For V2 Compat
from Shine.Lustre.Actions.Action import ErrorResult

# SHINE PROXY PROTOCOL CONSTANTS
SHINE_MSG_MAGIC = "SHINE:"
SHINE_MSG_VERSION = 3

class ProxyActionUnpackError(Exception):
    """
    An error occured while trying to unpack a shine event message.
    """

class ProxyAction(Action):
    """
    Abstract shine proxy action class.
    """

    NAME = 'proxy'

    def __init__(self, task=task_self()):
        Action.__init__(self, task)
        self.progpath = os.path.abspath(sys.argv[0])

    def _shine_msg_unpack(self, msg):
        """
        Parse a raw string from a remote shine command.
        Return a dict containing the information put by
         RemoteCallEventHandler._shine_msg_pack()
        """
        # check for any shine msg
        if not msg.startswith("SHINE:"):
            raise ProxyActionUnpackError("Missing shine message prefix")

        # Identified shine msg of the form SHINE:<version>:<pickle>
        try:
            # unpack pickle object
            version, data = msg[6:].split(':', 1)
            if int(version) == SHINE_MSG_VERSION:
                return pickle.loads(binascii.a2b_base64(data))
            elif int(version) == 2:
                return self._shine_msg_unpack_v2(data)
            else:
                raise ProxyActionUnpackError("Shine message version mismatch")
        except Exception, exp:
            raise ProxyActionUnpackError("Unknown error: %s" % exp)

    @classmethod
    def _shine_msg_unpack_v2(cls, msg):
        """Compatibility function to unpack old-style v2 messages."""
        # v2 message looks like:
        # SHINE:2:ev_starttarget_done:{node:, comp:, rc:, message:}

        event, msg = msg.split(':', 1)
        data = pickle.loads(binascii.a2b_base64(msg))
        dummy, actioncomp, data['status'] = event.split('_', 3)
        for name in ('router', 'client', 'target', 'journal'):
            if actioncomp.endswith(name):
                data['action'] = actioncomp[:-len(name)]
                data['compname'] = name
                break

        # Result is only possible for 'failed' event in v2.
        if data['status'] == 'failed':
            data['result'] = ErrorResult(message=data.get('message'),
                                         retcode=data.get('rc'))
        return data

class FSProxyAction(ProxyAction):
    """
    Generic file system command proxy action class.
    """

    def __init__(self, fs, action, nodes, debug, comps=None, addopts=None, 
                 failover=None, mountdata=None):

        ProxyAction.__init__(self)
        self.fs = fs
        self.action = action
        self.nodes = nodes
        self.debug = debug

        self._comps = comps

        self.addopts = addopts
        self.failover = failover
        self.mountdata = mountdata

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
            command.append("-l %s" % self._comps.labels())

        if self.addopts:
            command.append("-o '%s'" % self.addopts)

        if self.failover:
            command.append("-F '%s'" % self.failover)

        if self.mountdata:
            command.append('--mountdata')

        # Schedule cluster command.
        self.task.shell(' '.join(command), nodes=self.nodes, handler=self)

        # Launch events
        self._actions_start()

    def _actions_start(self):
        """
        Raise 'proxy' events for all components related to this ProxyAction.
        """
        # Add a 'proxy' running action for each component.
        if self._comps:
            for comp in self._comps:
                # Warning: there is no clean call at the end of the action.
                # cleaning is done by hand.
                comp.action_start('proxy')

    def ev_read(self, worker):
        node, buf = worker.last_read()
        try:
            data = self._shine_msg_unpack(buf)
            compname = data.pop('compname')
            action = data.pop('action')
            status = data.pop('status')
            self.fs.distant_event(compname, action, status, node=node, **data)
        except ProxyActionUnpackError:
            # ignore any non shine messages
            pass

    def ev_close(self, worker):
        """
        End of proxy command.
        """

        # XXX: Before all, we must check if shine command ran without
        # bugs, node crash, etc... So we need to verify all node retcode
        # and change the component state on the bad nodes.


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
                    actions = ""
                    if len(comp._list_action()):
                        actions = "actions: " + ", ".join(comp._list_action())
                    print >> sys.stderr, "ERROR: bad state for %s: %d %s" % \
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
                    self.fs._handle_shine_proxy_error(nodes, "Remote action "
                                                      "%s failed: %s" %
                                                      (self.action, buf))

                # Raise an error for nodes without outputs
                if len(nobuffer_nodes) > 0:
                    self.fs._handle_shine_proxy_error(nobuffer_nodes, \
                        "Remote action %s failed: No response" % (self.action))
