# BackendRegistry.py -- Registry for config backends
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

from Backend import Backend

from Shine.Configuration.Globals import Globals


class BackendRegistry:
    """ Container object to deal with available storage systems.
    """
    def __init__(self):
        self.backend_list = []
        self.backend_dict = {}

    # Special methods

    def __len__(self):
        "Return the number of backend storages."
        return len(self.backend_list)
    
    def __iter__(self):
        "Iterate over available backend storages."
        for backend in self.backend_list:
            yield backend

    # Public methods

    def get(self, name):

        if name == "None":
            return None

        # Import Backend if not already done
        if name not in self.backend_dict:
            try:
                mod = __import__(name, globals(), locals(), [])
                cls = getattr(mod, mod.BACKEND_MODNAME)
                self.register(cls())
            except Exception, e:
                raise

        return self.backend_dict[name]

    def get_selected(self):
        return self.get(Globals().get_backend())

    def register(self, obj):
        "Register a new config backend storage system."
        if not isinstance(obj, Backend):
            raise something
        self.backend_list.append(obj)
        #print "adding %s" % obj.get_name()
        self.backend_dict[obj.get_name()] = obj

    
