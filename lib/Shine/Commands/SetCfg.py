# SetCfg.py -- Shine setup
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *
from Base.Command import Command

from Shine.Utilities.Cluster.NodeSet import NodeSet
from Shine.Utilities.Cluster.Task import Task

import getopt
import os
import sys

# ----------------------------------------------------------------------
# * shine set_cfg
# ----------------------------------------------------------------------
class SetCfg(Command):
    def get_name(self):
        return "set_cfg"

    def get_params_desc(self):
        return "-n <I/O nodes list>"

    def get_desc(self):
        return "Set shine config on Lustre servers."

    def execute(self, args):
        try:
            nodes = None
            options, arguments = getopt.getopt(args, "n:")
            for opt, arg in options:
                if opt == '-n':
                    nodes = arg
            if not nodes:
                print "Error: use -n to specify I/O nodes list/range(s)"
                sys.exit(1)
            else:
                src = dst = "/etc/shine/shine.conf"
                #f2 = "/etc/shine/storage.conf"
                task = Task.current()
                worker1 = task.copy(src, dst, nodes=NodeSet(nodes))
                #worker2 = task.copy(f2, f2, nodes=NodeSet(nodes))
                task.run()

                gdict = worker1.gather_rc()
                for nodelist, rc in gdict.iteritems():
                    if rc != 0:
                        print "set_cfg failed on %s: %s" % (nodelist.as_ranges(), os.strerror(rc))
                        print "Please verify that shine is correctly installed on these nodes."
                        sys.exit(1)
                    elif rc == 0:
                        print "set_cfg successful on %s" % nodelist.as_ranges()

                """
                gdict = worker2.gather_rc()
                for nodelist, rc in gdict.iteritems():
                    if rc != 0:
                        print "set_cfg failed on %s: %s" % (nodelist.as_ranges(), os.strerror(rc))
                        print "Please verify that shine is correctly installed on these nodes."
                        sys.exit(1)
                    elif rc == 0:
                        print "set_cfg successful on %s" % nodelist.as_ranges()
                """


        except getopt.GetoptError:
            raise
        except ConfigException, e:
            print e
        except IOError, e:
            print e

