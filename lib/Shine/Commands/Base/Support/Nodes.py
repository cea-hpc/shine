# Nodes.py -- Impl. class for -n node option
# Copyright (C) 2008, 2009 CEA
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


from ClusterShell.NodeSet import NodeSet

class Nodes:
    """
    Command support class for "-n <nodeset> and -x <nodeset>" command option.
    """
    
    def __init__(self, cmd, optional=True):

        attr = { 'optional' : optional,
                 'hidden' : False,
                 'doc' : "node, comma-separated list of nodes or nodeset, eg. red[2-10/2]" }

        self.cmd = cmd
        self.cmd.add_option('n', 'nodes', attr)

        attr = { 'optional' : optional,
                 'hidden' : False,
                 'doc' : "exclude node, comma-separated list of nodes or nodeset, eg. red[2-10/2]" }
        self.cmd.add_option('x', 'excludes', attr)
    
    def get_nodeset(self):
        if self.cmd.opt_n:
            return NodeSet(self.cmd.opt_n)

        return None

    def get_excludes(self):
        if self.cmd.opt_x:
            return NodeSet(self.cmd.opt_x)

        return None

    def check_valid_list(self, fs_name, fs_nodes, action_txt="do"):
        """
        This helper method verifies, for the provided filesystem, that the
        nodesets possibly set on command line, to restrain the node list, did
        not:
         - disabled all nodes
         - specified nodes which are not in filesystem configuration.
        Return False if nothing was done.
        """

        selected_nodes = self.get_nodeset()
        excluded_nodes = self.get_excludes()

        # Is there unknown host?
        if selected_nodes:
            if excluded_nodes:
                selected_nodes = selected_nodes - excluded_nodes
            if fs_nodes:
                selected_nodes = selected_nodes - fs_nodes
            if selected_nodes:
                print "WARNING: Nothing to %s on %s for `%s'." % \
                    (action_txt, selected_nodes, fs_name)
        
        # All nodes were disabled?
        if len(fs_nodes) == 0:
            print "WARNING: Nothing was done for `%s'." % fs_name
            return False

        return True
