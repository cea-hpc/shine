# Stop.py -- Lustre proxy action class : stop
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

from ProxyAction import ProxyAction

from Shine.Utilities.Cluster.NodeSet import NodeSet
from Shine.Utilities.Cluster.Event import EventHandler
from Shine.Utilities.Cluster.Task import Task
from Shine.Utilities.Cluster.Worker import Worker
from Shine.Utilities.AsciiTable import AsciiTable, AsciiTableLayout

import binascii, pickle

class Stop(ProxyAction):
    """
    File system stop proxy action class.
    """

    def __init__(self, task, fs, target_name):
        ProxyAction.__init__(self, task)
        self.fs = fs
        self.target_name = target_name
        assert self.target_name != None
        self.tgt_list = []

    def get_tgt_list(self):
        return self.tgt_list

    def launch(self):
        """
        Proxy file system stop command to target.
        """

        # Prepare proxy command
        command = "%s stop -f %s -R -t %s" % (self.progpath, self.fs.fs_name, self.target_name)

        selected_nodes = self.fs.get_target_nodes(self.target_name)

        # Run cluster command
        self.task.shell(command, nodes=selected_nodes, handler=self)
        self.task.run()

    def ev_read(self, worker):
        node, info = worker.get_last_read()
        dic = pickle.loads(binascii.a2b_base64(info))

        msg = dic['msg']

        dic['status'] = "UNKNOWN"

        if msg == "STOPPING":
            print "Stopping %s (%s) on %s" % (dic['target'], dic['dev'], node)
        elif msg == "UMOUNTING":
            print "Unmounting %s on %s" % (dic['fs'], node)
        elif msg == "RESULT":
            if dic['rc'] == 0:
                dic['status'] = "STOPPED"
            else:
                if dic['buf'].find("not mounted") == -1:
                    dic['status'] = "STOP FAILED"

                    print "Stopping of %s (%s) on node %s failed with error %d" % (dic['target'],
                        dic['dev'], node, dic['rc'])
                    print "%s: %s" % (node, dic['buf'].strip())
                else:
                    dic['status'] = "ALREADY STOPPED"
                    
            dic["node"] = node
            self.tgt_list.append(dic)


    def ev_close(self, worker):
        pass
