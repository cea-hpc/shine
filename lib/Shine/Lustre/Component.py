# Components.py - Abstract class for any Lustre filesystem components.
# Copyright (C) 2010 CEA
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

# Constants for component states
(MOUNTED,    \
 EXTERNAL,   \
 RECOVERING, \
 OFFLINE,    \
 INPROGRESS, \
 CLIENT_ERROR, \
 TARGET_ERROR, \
 RUNTIME_ERROR) = range(8)

class Component(object):
    """
    Abstract class for all common part of all Lustre filesystem 
    components.
    """

    # Text name for this component
    TYPE = "(should be overridden)"

    # Each component knows which component it depends on.
    # Its start order should be this component start order + 1.
    # This value will be use to sort the components when starting.
    START_ORDER = 0

    # Order used when displaying a list of components
    DISPLAY_ORDER = 0

    # Text mapping for each possible states
    STATE_TEXT_MAP = {}

    def __init__(self, fs, server, enabled = True):

        # File system
        self.fs = fs

        # Each component resides on one server
        self.server = server

        # Status
        self.state = None

        # Text hint of component status
        self.status_info = None

        # Enabled or not
        self.action_enabled = enabled

    #
    # Serializing methods.
    # Pickle representation do not include filesystem pointer.
    #
    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        self.state = other.state
        self.status_info = other.status_info

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['fs']
        return odict

    def __setstate__(self, dict):
        self.__dict__.update(dict)
        self.fs = None

    # 
    # Component printing methods.
    #

    def text_status(self):
        """
        Return a human text form for the component state.
        """
        return self.STATE_TEXT_MAP.get(self.state, "BUG STATE %d" % self.state)

