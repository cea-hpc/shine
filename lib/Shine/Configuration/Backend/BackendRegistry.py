# BackendRegistry.py -- Registry for config backends
# Copyright (C) 2007,2013 CEA
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

"""
Load and maintain the list of available configuration backends.
"""

from Shine.Configuration.Globals import Globals

class BackendRegistry:
    """Container object to deal with available storage systems."""

    def __init__(self):
        self.backends = {}

    def __len__(self):
        """Return the number of backend storages."""
        return len(self.backends)
    
    def __iter__(self):
        """Iterate over available backend storages."""
        for backend in self.backends.values():
            yield backend

    def get(self, name):
        """Load an return a instance of backend with the specified name."""

        if name == "None":
            return None

        # Import Backend if not already done
        if name not in self.backends:
            mod = __import__(name, globals(), locals(), [])
            cls = getattr(mod, mod.BACKEND_MODNAME)
            self.register(cls())

        return self.backends[name]

    def selected(self):
        """Return the Backend specified in global configuration."""
        return self.get(Globals().get_backend())

    def register(self, obj):
        """Register a new config backend storage system."""
        self.backends[obj.get_name()] = obj

