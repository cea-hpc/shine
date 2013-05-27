# Mount.py -- Mount file system clients
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
from Base.FSClientCommand import FSClientCommand

# ----------------------------------------------------------------------
# * shine mount
# ----------------------------------------------------------------------
class Mount(FSClientCommand):

    def get_name(self):
        return "mount"

    def get_params_desc(self):
        return "-f <fsname> -n <nodes>"

    def get_desc(self):
        return "Mount file system client(s)."

    def fs_execute(self, fs, nodes=None):
        """
        fs_conf_dir = os.path.expandvars(Globals.get_one('conf_dir'))
        fs_conf_dir = os.path.normpath(fs_conf_dir)

        f1 = "%s/%s.xmf" % (fs_conf_dir, fs)
        task = Task.current()
        worker1 = task.copy(f1, f1, nodes=NodeSet(nodes))
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
        fs.mount(nodes)

