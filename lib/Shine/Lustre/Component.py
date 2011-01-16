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

class ComponentError(Exception):
    """Generic exception for any components."""

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

    def __init__(self, fs, server, enabled = True, mode = 'managed'):

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

        # List of running action
        self.__running_actions = []

        # Component behaviour change depending on its mode.
        self._mode = mode

        self.fs._attach_component(self)

    @property
    def label(self):
        """
        Return the component label. 
        It contains the filesystem name and component type.
        """
        return "%s-%s" % (self.fs.fs_name, self.TYPE)

    def uniqueid(self):
        """Return a unique string representing this component."""
        return "%s-%s" % (self.label, ','.join(self.server.nids))

    def longtext(self):
        """
        Return a string describing this component, for output purposes.
        """
        return self.label

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
    # Component behaviour
    #
  
    def capable(self, action):
        # Do I implement this method?
        #XXX: Presently, the check do not check this is callable.
        # This is used for testing 'label' by example.
        return hasattr(self, action) 

    def is_external(self):
        return self._mode == 'external'
 
    # 
    # Component printing methods.
    #

    def text_status(self):
        """
        Return a human text form for the component state.
        """
        return self.STATE_TEXT_MAP.get(self.state, "BUG STATE %s" % self.state)


    #
    def lustre_check(self):
        """
        Check component health at Lustre level.
        """
        raise NotImplemented("Component must implement this.")


    #
    # Inprogress action methods
    #
    def _add_action(self, act, comp=None):
        """
        Add the named action to the running action list.
        """
        if not comp:
            comp = self.TYPE
        assert((act, comp) not in self.__running_actions)
        self.__running_actions.append((act, comp))

    def _del_action(self, act, comp=None):
        """
        Remove the named action from the running action list.
        """
        if not comp:
            comp = self.TYPE
        self.__running_actions.remove((act, comp))

    def _list_action(self):
        """
        Return the running action list.
        """
        return self.__running_actions

    #
    # Event raising methods
    #

    def _action_start(self, act, comp=None):
        """Called by Actions.* when starting"""
        if not comp:
            comp = self.TYPE
        self._add_action(act, comp)
        self.fs._invoke('ev_%s%s_start' % (act, comp), comp=self)

    def _action_done(self, act, comp=None):
        """Called by Actions.* when done"""
        if not comp:
            comp = self.TYPE
        self._del_action(act, comp)
        self.fs._invoke('ev_%s%s_done' % (act, comp), comp=self)

    def _action_timeout(self, act, comp=None):
        """Called by Actions.* on timeout"""
        if not comp:
            comp = self.TYPE
        self._del_action(act, comp)
        self.fs._invoke('ev_%s%s_timeout' % (act, comp), comp=self)

    def _action_failed(self, act, rc, message, comp=None):
        """Called by Actions.* on failure"""
        if not comp:
            comp = self.TYPE
        self._del_action(act, comp)
        self.fs._invoke('ev_%s%s_failed' % (act, comp), comp=self, rc=rc, 
                        message=message)
