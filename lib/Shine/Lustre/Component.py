# Components.py - Abstract class for any Lustre filesystem components.
# Copyright (C) 2010-2015 CEA
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

import sys

from itertools import ifilter, groupby
from operator import attrgetter, itemgetter

from ClusterShell.NodeSet import NodeSet

# Constants for component states.
# Error codes should have the largest values, see FileSystem._check_errors()
MOUNTED = 0
EXTERNAL = 1
RECOVERING = 2
OFFLINE = 3
INPROGRESS = 4
CLIENT_ERROR = 5
TARGET_ERROR = 6
RUNTIME_ERROR = 7
INACTIVE = 8
MIGRATED = 9
NO_DEVICE = 10

from Shine.Lustre import ComponentError
from Shine.Lustre.Server import ServerGroup
from Shine.Lustre.Actions.Status import Status
from Shine.Lustre.Actions.Execute import Execute

class Component(object):
    """
    Abstract class for all common part of all Lustre filesystem components.
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

    def __init__(self, fs, server, enabled = True, mode = 'managed',
                 active = 'manual'):

        # File system
        self.fs = fs

        # Each component resides on one server
        self.server = server

        # Status
        self.state = None

        # Enabled or not
        self.action_enabled = enabled

        # List of running action
        self._running_actions = []

        # Component behaviour change depending on its mode.
        self._mode = mode

        # Component active state
        self.active = active

    @property
    def label(self):
        """
        Return the component label. 
        It contains the filesystem name and component type.
        """
        return "%s-%s" % (self.fs.fs_name, self.TYPE)

    def allservers(self):
        """
        Return all servers this target can run on. On standard component
        there is only one server.
        """
        return ServerGroup([self.server])

    def uniqueid(self):
        """Return a unique string representing this component."""
        return "%s-%s" % (self.label, ','.join(self.server.nids))

    def longtext(self):
        """
        Return a string describing this component, for output purposes.
        """
        return self.label

    def update_server(self):
        """
        Compute the server to display for the component.
        This method does nothing on all components except for Target ones.
        """
        pass

    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        self.state = other.state

    def sanitize_state(self, nodes=None):
        """
        Clean component state if it is wrong.
        """
        if self.state is None:
            self.state = RUNTIME_ERROR

        # At this step, there should be no more INPROGRESS component.
        # If yes, this is a bug, change state to RUNTIME_ERROR.
        # INPROGRESS management could be change using running action
        # list.
        # Starting with v1.3, there is no more code setting INPROGRESS.
        # This is for compatibility with older clients.
        elif self.state == INPROGRESS:
            actions = ""
            if len(self._list_action()):
                actions = "actions: " + ", ".join(self._list_action())
            print >> sys.stderr, "ERROR: bad state for %s: %d %s" % \
                            (self.label, self.state, actions)
            self.state = RUNTIME_ERROR

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['fs']
        return odict

    def __setstate__(self, state):
        self.__dict__.update(state)
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
 
    def is_active(self):
        return self.active != 'no'

    # 
    # Component printing methods.
    #

    def text_statusonly(self):
        """
        Return a string version of the component state, only.
        """
        return Component.text_status(self)

    def text_status(self):
        """
        Return a human text form for the component state.
        """
        return self.STATE_TEXT_MAP.get(self.state, "BUG STATE %s" % self.state)

    #
    # State checking methods.
    #
    def lustre_check(self):
        """
        Check component health at Lustre level.
        """
        raise NotImplementedError("Component must implement this.")

    def full_check(self, mountdata=True):
        """
        Check component states, at Lustre level, and any other required ones.
        """
        self.lustre_check()

    #
    # Inprogress action methods
    #
    def _add_action(self, act):
        """
        Add the named action to the running action list.
        """
        self._running_actions.append(act)

    def _del_action(self, act):
        """
        Remove the named action from the running action list.
        """
        self._running_actions.remove(act)

    def _list_action(self):
        """
        Return the running action list.
        """
        return self._running_actions

    #
    # Event raising method
    #

    def action_event(self, act, status, result=None):
        """Send an event."""
        if status == 'start':
            self._add_action(act.NAME)
        elif status in ('done', 'timeout', 'failed'):
            self._del_action(act.NAME)
        self.fs.local_event('comp', info=act.info(), status=status,
                            result=result)

    #
    # Helper methods to check component state in Actions.
    #

    def is_started(self):
        """Return True if the component is started."""
        return self.state == MOUNTED

    def is_stopped(self):
        """Return True if the component is stopped."""
        return self.state == OFFLINE

    #
    # Component common actions
    #

    def status(self, **kwargs):
        """Check component status."""
        return Status(self, **kwargs)

    def execute(self, **kwargs):
        """Exec a custom command."""
        return Execute(self, **kwargs)

class ComponentGroup(object):
    """
    Gather and efficiently manipulate list of Components.
    """

    def __init__(self, iterable=None):
        self._elems = {}
        if iterable:
            self._elems = dict([(comp.uniqueid(), comp) for comp in iterable])

    def __len__(self):
        return len(self._elems)

    def __iter__(self):
        return self._elems.itervalues()

    def __contains__(self, comp):
        return comp.uniqueid() in self._elems

    def __getitem__(self, key):
        return self._elems[key]

    def __str__(self):
        return str(self.labels())

    def add(self, component):
        """
        Add a new component to the group. 
        
        Raises a KeyError if a component
        with the same uniqueid() is already added.
        """
        if component in self:
            raise KeyError("A component with id %s already exists." %
                           component.uniqueid())
        self._elems[component.uniqueid()] = component
 
    def update(self, iterable):
        """
        Insert all components from iterable.
        """
        for comp in iterable:
            self.add(comp)

    def __or__(self, other):
        """
        Implements the | operator. So s | t returns a new group with
        elements from both s and t.
        """
        if not isinstance(other, ComponentGroup):
            return NotImplemented 
        grp = ComponentGroup()
        grp.update(iter(self))
        grp.update(iter(other))
        return grp

    #
    # Useful getters
    #

    def labels(self):
        """Return a NodeSet containing all component label."""
        return NodeSet.fromlist((comp.label for comp in self))

    def servers(self):
        """Return a NodeSet containing all component servers."""
        return NodeSet.fromlist((comp.server.hostname for comp in self))

    def allservers(self):
        """Return a NodeSet containing all component servers and fail
        servers."""
        servers = self.servers()
        for comp in self.filter(supports='failservers'):
            servers.update(comp.failservers.nodeset())
        return servers

    #
    # Filtering methods
    #

    def filter(self, supports=None, key=None):
        """
        Returns a new ComponentGroup instance containing only the component
        that matches the filtering rules.

        Your own filtering rule could be defined using the key argument.

        Example: Return only the OST from the group
        >>> group.filter(key=lambda t: t.TYPE == OST.TYPE)
        """
        if supports and not key:
            filter_key = lambda x: x.capable(supports)
        elif supports and key:
            filter_key = lambda x: key(x) and x.capable(supports)
        else:
            filter_key = key

        return ComponentGroup(ifilter(filter_key, iter(self)))

    def enabled(self):
        """Uses filter() to return only the enabled components."""
        key = attrgetter('action_enabled')
        return self.filter(key=key)

    def managed(self, supports=None, inactive=False):
        """Uses filter() to return only the enabled and managed components."""
        if inactive == True:
            # targets that are inactive _and_ external are also selected
            key = lambda comp: comp.action_enabled and \
                               ((not comp.is_external()) or \
                               (comp.is_external() and not comp.is_active()))
        else:
            key = lambda comp: comp.action_enabled and \
                               not comp.is_external() and \
                               comp.is_active()
        return self.filter(supports, key=key)

    #
    # Grouping methods
    #

    def groupby(self, attr=None, key=None, reverse=False):
        """Return an iterator over the group components. 
        
        The component will be grouped using one of their attribute or using a
        custom key.
        
        Example #1: Group component by type
        >>> for comp_type, comp_list in group.groupby(attr='TYPE'):
        ...

        Example #2: Group component first by type, then by server
        >>> key = lambda t: (t.TYPE, t.server)
        >>> for comp_type, comp_list in group.groupby(key=key):
        ...
        """
        assert (not (attr and key)), "Unsupported: attr and supports"

        if key is None and attr is not None:
            key = attrgetter(attr)

        # Sort the components using the key, and then group results 
        # using the same key.
        sortlist = sorted(iter(self), key=key, reverse=reverse)
        grouped = groupby(sortlist, key)
        return ((grpkey, ComponentGroup(comps)) for grpkey, comps in grouped)

    def groupbyallservers(self):
        """
        Group components per server taking into account
        all possible servers for each component.
        """
        # Create a list of (server, component) tuples
        srvcomps = []
        for comp in self:
            for srv in comp.allservers():
                srvcomps.append((srv, comp))

        # Sort the components using the server name in each tuple as key,
        # and then, group results using the same key.
        sortlist = sorted(srvcomps, key=itemgetter(0))
        grouped = groupby(sortlist, key=itemgetter(0))

        return ((grpkey, ComponentGroup(map(itemgetter(1), tpl)))
                for grpkey, tpl in grouped)


    def groupbyserver(self, allservers=False):
        """Uses groupby() to group component per server."""
        if allservers is False:
            return self.groupby(attr='server')
        else:
            return self.groupbyallservers()
