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
#from Shine.Utilities.AsciiTable import AsciiTable, AsciiTableLayout


import binascii, pickle


class Status(ProxyAction):
    """
    File system status proxy action class.
    """

    def __init__(self, task, fs, target_name=None):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.target_name = target_name
        self._tgt_list = []

    def launch(self):
        """
        Proxy file system targets status.
        """

        # Prepare proxy command
        if self.target_name:
            command = "%s status -f %s -R -t %s" % (self.progpath, self.fs.fs_name, self.target_name)
        else:
            command = "%s status -f %s -R" % (self.progpath, self.fs.fs_name)

        selected_nodes = self.fs.get_target_nodes(self.target_name)

        # Run cluster command
        self.task.shell(command, nodes=selected_nodes, handler=self)
        self.task.run()

    def ev_read(self, worker):
        node, info = worker.get_last_read()
        dic = pickle.loads(binascii.a2b_base64(info))
        dic["node"] = node
        self._tgt_list.append(dic)

    def ev_close(self, worker):
        #gdict = worker.gather()
        #print gdict

        try:
            CommandRegistry.output(fs=self.fs.fs_name, listofdic=self._tgt_list)

        except Exception, e:
            print e
            raise

        gdict = worker.gather_rc()
        for nodelist, rc in gdict.iteritems():
            if rc != 0:
                if self.target_name:
                    raise ActionFailedError(rc,
                        "Status of %s failed on %s" % (self.target_name.upper(),
                            nodelist.as_ranges()))
                else:
                    raise ActionFailedError(rc,
                        "Status failed on %s" % nodelist.as_ranges())

    
