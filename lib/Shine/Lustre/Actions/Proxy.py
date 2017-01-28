# Proxy.py -- Lustre generic FS proxy action class
# Copyright (C) 2009-2015 CEA
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

import binascii, pickle

from ClusterShell.MsgTree import MsgTree
from ClusterShell.NodeSet import NodeSet

from Shine.Lustre.Component import INPROGRESS, RUNTIME_ERROR
from Shine.Lustre.Actions.Action import Action, CommonAction, ActionInfo, \
                                        ACT_OK, ACT_ERROR

# For V2 Compat
from Shine.Lustre.Actions.Action import ErrorResult

#
# SHINE PROXY PROTOCOL
#
SHINE_MSG_MAGIC = "SHINE:"
SHINE_MSG_VERSION = 3

class ProxyActionUnpackError(Exception):
    """An error occured while trying to unpack a shine event message."""

class ProxyActionUnpickleError(Exception):
    """An error occured while trying to unpickle a shine event message."""

def shine_msg_pack(**kwargs):
    """Shine event serialization method."""
    # To be more evolutive, Shine message contains only a dict.
    return "%s%d:%s" % (SHINE_MSG_MAGIC, SHINE_MSG_VERSION,
                        binascii.b2a_base64(pickle.dumps(kwargs, -1)))

def shine_msg_unpack(msg):
    """
    Parse a raw string from a remote shine command.

    Return a dict containing the information put by shine_msg_pack().
    """
    # check for any shine msg
    if not msg.startswith(SHINE_MSG_MAGIC):
        raise ProxyActionUnpackError("Missing shine message prefix")

    # Identified shine msg of the form SHINE:<version>:<pickle>
    try:
        version, data = msg[len(SHINE_MSG_MAGIC):].split(':', 1)
        version = int(version)
    except Exception, exp:
        raise ProxyActionUnpackError("Malformed Shine message: %s" % exp)

    if version == SHINE_MSG_VERSION:
        try:
            # unpack and unpickle object
            return pickle.loads(binascii.a2b_base64(data))
        except Exception, exp:
            msg = "Cannot unpickle message (check Shine and ClusterShell " \
                  "versions): %s" % exp
            raise ProxyActionUnpickleError(msg)

    elif version == 2:
        try:
            return shine_msg_unpack_v2(data)
        except Exception, exp:
            raise ProxyActionUnpackError("Unknown error: %s" % exp)

    else:
        raise ProxyActionUnpackError("Shine message version mismatch")

def shine_msg_unpack_v2(msg):
    """
    Compatibility function to unpack old-style v2 messages.

    v2-style messages were used up to v0.910, becoming useless when
    v3-style messages were introduced in v0.911, released 14-02-12.
    """
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


class FSProxyAction(CommonAction):
    """
    Generic file system command proxy action class.
    """

    NAME = 'proxy'

    def __init__(self, fs, action, nodes, debug, comps=None, **kwargs):

        CommonAction.__init__(self)

        self.fs = fs
        self.action = action
        self.nodes = nodes
        self.debug = debug

        self._comps = comps

        self.options = {}
        for optname in ('addopts', 'failover', 'mountdata', 'fanout',
                        'dryrun'):
            self.options[optname] = kwargs.get(optname)

        self._outputs = MsgTree()
        self._errpickle = MsgTree()
        self._silentnodes = NodeSet() # Error nodes without output

        if self.fs.debug:
            print "FSProxyAction %s on %s" % (action, nodes)

    def info(self):
        return ActionInfo(self, description='Proxy action')

    def _prepare_cmd(self):
        """Create the command line base on proxy properties."""

        command = ["shine"] # launch remote shine executable
        command.append(self.action)
        command.append("-f %s" % self.fs.fs_name)
        command.append("-R")

        if self.debug:
            command.append("-d")

        if self._comps:
            command.append("-l %s" % self._comps.labels())

        if self.options['addopts']:
            command.append("-o '%s'" % self.options['addopts'])

        if self.options['failover']:
            command.append("-F '%s'" % self.options['failover'])

        if self.options['fanout'] is not None:
            command.append('--fanout=%d' % self.options['fanout'])

        if self.options['dryrun']:
            command.append('--dry-run')

        # To be compatible with older clients in most cases, do not set the
        # option when it is its default value.
        if self.options['mountdata'] not in (None, 'auto'):
            command.append('--mountdata=%s' % self.options['mountdata'])

        return command

    def _launch(self):
        """Launch FS proxy command."""
        command = self._prepare_cmd()

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
                # This special event is raised to keep track of undergoing
                # actions. Maybe this could be dropped is such tracking is no
                # more needed.
                comp.action_event(self, 'start')

    def ev_read(self, worker):
        node = worker.current_node
        buf = worker.current_msg
        try:
            data = shine_msg_unpack(buf)

            # COMPAT: Prior to 1.4, 'comp'+'action' was used.
            # 1.4+ uses ActionInfo
            if 'comp' in data:
                action = Action()
                action.NAME = data.pop('action')
                comp = data.pop('comp')
                comp.fs = self.fs
                desc = "%s of %s" % (action.NAME, comp.longtext())
                data['info'] = ActionInfo(action, comp, desc)
                evtype = 'comp'
            else:
                evtype = data.pop('evtype')

            self.fs.distant_event(evtype, node=node, **data)
        except ProxyActionUnpickleError, exp:
            # Maintain a standalone list of unpickling errors.
            # Node could have unpickling error but still exit with 0
            msg = str(exp)
            if msg not in self._errpickle.get(node, ""):
                self._errpickle.add(node, msg)
        except AttributeError, exp:
            msg = "Cannot read message (check Shine and ClusterShell " \
                  "version): %s" % str(exp)
            if msg not in self._errpickle.get(node, ""):
                self._errpickle.add(node, msg)
        except ProxyActionUnpackError:
            # Store output that is not a shine message
            self._outputs.add(node, buf)

    def ev_hup(self, worker):
        """Keep a list of node, without output, with a return code != 0"""
        # If this node was on error
        if worker.current_rc != 0:
            # If there is no known outputs
            if self._outputs.get(worker.current_node) is None:
                self._silentnodes.add(worker.current_node)

    def ev_close(self, worker):
        """End of proxy command."""
        Action.ev_close(self, worker)

        # Before all, we must check if shine command ran without bugs, node
        # crash, etc...
        # So we need to verify all node retcodes and change the component state
        # on the bad nodes.

        # Action timed out
        if worker.did_timeout():
            self.set_status(ACT_ERROR)
            return

        status = ACT_OK

        # Remove the 'proxy' running action for each component.
        if self._comps:
            for comp in self._comps:
                # This special event helps to keep track of undergoing actions
                # (see ev_start())
                comp.action_event(self, 'done')
                comp.sanitize_state(nodes=worker.nodes)

        # Gather nodes by return code
        for rc, nodes in worker.iter_retcodes():
            # Remote command returns only RUNTIME_ERROR (See RemoteCommand)
            # some common remote errors:
            # rc 127 = command not found
            # rc 126 = found but not executable
            # rc 1 = python failure...
            if rc != 0:

                # If there is at least one error, the action is on error.
                status = ACT_ERROR

                # Gather these nodes by buffer
                key = nodes.__contains__
                for buffers, nodes in self._outputs.walk(match=key):
                    # Handle proxy command error
                    nodes = NodeSet.fromlist(nodes)
                    msg = "Remote action %s failed: %s\n" % \
                                                        (self.action, buffers)
                    self.fs._handle_shine_proxy_error(nodes, msg)

        # Raise errors for each unpickling error,
        # which could happen mostly when Shine exits with 0.
        for buffers, nodes in self._errpickle.walk():
            nodes = NodeSet.fromlist(nodes)
            self.fs._handle_shine_proxy_error(nodes, str(buffers))

        # Raise an error for nodes without output
        if len(self._silentnodes) > 0:
            msg = "Remote action %s failed: No response" % self.action
            self.fs._handle_shine_proxy_error(self._silentnodes, msg)

        self.set_status(status)
