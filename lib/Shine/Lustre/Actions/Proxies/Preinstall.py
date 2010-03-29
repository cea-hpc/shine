# Preinstall.py -- Create shine Lustre FS config directories
# Copyright (C) 2007, 2009 CEA
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

from Shine.Lustre.Actions.Proxies.ProxyAction import ProxyAction, ProxyActionError

from ClusterShell.NodeSet import NodeSet

class Preinstall(ProxyAction):
    """
    Action class: install file system configuration requirements on remote nodes.
    """

    def __init__(self, nodes, fs):
        ProxyAction.__init__(self)
        self.nodes = nodes
        self.fs = fs

    def launch(self):
        """
        Launch proxy preinstall command.
        """
        command = "%s preinstall -f %s -R" % (self.progpath, self.fs.fs_name)

        # Schedule command for execution
        self.worker = self.task.shell(command, nodes=self.nodes, handler=self, timeout=2)

    def ev_close(self, worker):
        """
        Check for any erroneous return code.
        """
        # check for remote/ssh errors
        for rc, nodeset in worker.iter_retcodes():
            if rc != 0:
                message = "Cannot create file system configuration directories (preinstall)"
                more = worker.node_buffer(nodeset[0])
                if more:
                    message += "\nHint: %s" % more
                raise ProxyActionError(nodeset, message, rc)

        # check for timeout errors
        if worker.num_timeout() > 0:
            timeout_nodes = NodeSet.fromlist(worker.iter_keys_timeout())
            message = "Cannot create file system configuration directories (preinstall)"
            message += "\nHint: Timed out node(s)"
            raise ProxyActionError(timeout_nodes, message)
