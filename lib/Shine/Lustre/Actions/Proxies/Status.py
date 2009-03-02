# Status.py -- Lustre proxy action class : status
# Copyright (C) 2007 CEA
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

from Shine.Commands.CommandRegistry import CommandRegistry

from Shine.Lustre.Actions.Action import ActionFailedError
from ProxyAction import ProxyAction

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Event import EventHandler
from ClusterShell.Task import Task
from ClusterShell.Worker import Worker


class Status(ProxyAction):
    """
    File system status proxy action class.
    """

    def __init__(self, task, fs, target_name=None, view=None):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.target_name = target_name
        self.view = view
        self._clt_list = []
        self._tgt_list = []

        if self.view is None:
            self.view = 'overview'

    def launch(self):
        """
        Proxy file system targets status.
        """
        # Prepare cluster command.
        if self.target_name:
            command = "%s status -f %s -R -t %s -V %s" % (self.progpath,
                    self.fs.fs_name, self.target_name, self.view)
        else:
            command = "%s status -f %s -R -V %s" % (self.progpath,
                    self.fs.fs_name, self.view)

        selected_nodes = self.fs.get_target_nodes(self.target_name, True)
        #print "sel: %s" % selected_nodes

        # Submit command.
        self.task.shell(command, nodes=selected_nodes, handler=self,
                timeout=Globals().get_status_timeout())

    def ev_read(self, worker):
        node, msg = worker.last_read()
        #print node, msg
        dic = self._read_shine_msg(msg)
        if not dic:
            print "%s: %s" % (node, msg)
            return

        if dic.has_key('status_client'):

            # check if node info is correct (we never know...)
            if dic['node'] != node:
                print "Warning: node mismatch for %s (replied %s)" % (node, dic['node'])
                self._add_client(NodeSet(node), dic['fs'], dic['mount'], "node mismatch")
            else:
                self._add_client(NodeSet(node), dic['fs'], dic['mount'], dic['status_client'])

        elif dic.has_key('id'):
            # print dic
            dic["node"] = node
            self._tgt_list.append(dic)

        elif dic.has_key('health'):
            if dic['err'] == 2:
                print "%s: Lustre not started?" % node
            else:
                print "%s: %s (errno %d)" % (node, dic['health'], dic['err'])

    def ev_close(self, worker):

        # Check for timed out nodes.
        if worker.num_timeout() > 0:
            nodeset_timeout = NodeSet.fromlist(worker.iter_keys_timeout())
        else:
            nodeset_timeout = NodeSet()

        self._add_client(nodeset_timeout, self.fs.fs_name, "", "Error: timeout")

        for rc, nodelist in worker.iter_retcodes():
            if rc != 0:
                self._add_client(NodeSet.fromlist(nodelist), self.fs.fs_name,
                        "", "Error: %d" % rc)
        
        """
        for rc, nodeset in worker.iter_retcodes():
            if rc != 0:
                if self.target_name:
                    raise ActionFailedError(rc,
                        "Status of %s failed on %s" % (self.target_name.upper(), nodeset))
                else:
                    raise ActionFailedError(rc, "Status failed on %s" % nodeset)


        """


        #try:
        if len(self._tgt_list) > 0:
            CommandRegistry.output(fs=self.fs.fs_name,
                   tgt_listofdic=self._tgt_list)

        if len(self._clt_list) > 0:
            CommandRegistry.output(fs=self.fs.fs_name,
                    clt_listofdic=self._clt_list)

        """
        except Exception, e:
            print e
            raise
        """

        #raise ActionFailedError(rc, "")
    

    def _add_client(self, nodes, fs, mount, status_client):
        # compact nodes according to their status
        node_added = False
        ns = NodeSet(nodes)
        for d in self._clt_list:
            if d['status_client'] == status_client:
                ns = d['node']
                ns.update(nodes)
                d['node'] = ns
                d['nodecount'] = "%d" % len(ns)
                node_added = True
                break

        if not node_added:
            dic = { 'fs' : fs, 'node' : ns, "nodecount" : "%d" % len(ns),
                    'mount' : mount, 'status_client' : status_client }
            self._clt_list.append(dic)


