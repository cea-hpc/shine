# Target.py -- Impl. class for command target support 
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

from Shine.Commands.Exceptions import CommandBadParameterError

from ClusterShell.NodeSet import NodeSet


class Target:
    """
    Command support class for "-t <component_type>" command option.
    """

    def __init__(self, cmd):

        attr = { 'optional' : True,
                 'hidden' : False,
                 'doc' : "specify component (mgt, mdt, ost, router)" }

        self.cmd = cmd
        self.cmd.add_option('t', 'target', attr)

        attr = { 'optional' : True,
                 'hidden' : False,
                 'doc' : "specify component by label (ie: lustre-OST0000)" }
        self.cmd.add_option('l', 'label', attr)

        attr = { 'optional' : True,
                 'hidden' : False,
                 'doc' : "Nodes to use to fail over" }
        self.cmd.add_option('F', 'fail server', attr)



    def get_target(self):
        supported = [ 'mgt', 'mdt', 'ost', 'router' ]
        if self.cmd.opt_t:
            for t in self.cmd.opt_t.split(','):
                if t not in supported:
                    raise CommandBadParameterError(t, ", ".join(supported))
            return self.cmd.opt_t.lower()
        return None

    def get_labels(self):
        if self.cmd.opt_l:
            return NodeSet(self.cmd.opt_l)
        return None

    def get_failover(self):
        if self.cmd.opt_F:
            return NodeSet(self.cmd.opt_F)
        return None
