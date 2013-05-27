# Copyright (C) 2007 Bull S.A.S.
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


from Shine.Configuration.Backend.Backend import Backend

class ClusterDB(Backend):

    def __init__(self):
        Backend.__init__(self)

    def get_name(self):
        return "clusterdb"

    def get_desc(self):
        return "Bull ClusterDB Backend System."

    def start(self):
        """
        Called once when backend starts (use for DB connection initialization etc.)
        """
        raise NotImplementedError("To be implemented.")

    def get_target_devices(self, target):
        """
        Return a list of TargetDevice's
        """
        raise NotImplementedError("To be implemented.")
