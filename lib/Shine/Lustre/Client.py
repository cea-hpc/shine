# Client.py -- Lustre Client
# Copyright (C) 2008-2014 CEA
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
Classes for Shine framework to manage Lustre clients.
"""

from glob import glob
import os 
import re

from Shine.Lustre.Component import Component, ComponentError, \
                                   MOUNTED, OFFLINE, CLIENT_ERROR, RUNTIME_ERROR

from Shine.Lustre.Actions.StartClient import StartClient
from Shine.Lustre.Actions.StopClient import StopClient

from Shine.Lustre.Target import MDT, OST


class Client(Component):
    """
    Manage a Lustre client mount for a specific node.

    Client have a specific mount point and optionally some mount options.
    >>> client.mount_path
    >>> client.mount_options

    It can be started, stopped and check for status.
    """

    TYPE = 'client'
    DISPLAY_ORDER = max(MDT.DISPLAY_ORDER, OST.DISPLAY_ORDER) + 1 

    #
    # Text form for different client states. 
    #
    # Could be nearly merged with Target state_text_map if MOUNTED value
    # becomes the same.
    STATE_TEXT_MAP = { 
        None: "unknown",
        OFFLINE: "offline", 
        CLIENT_ERROR: "ERROR", 
        MOUNTED: "mounted", 
        RUNTIME_ERROR: "CHECK FAILURE" 
    }


    def __init__(self, fs, server, mount_path, mount_options=None,
                 subdir=None, enabled=True):
        """
        Initialize a Lustre client object.
        """
        self.mount_options = mount_options
        self.mount_path = mount_path
        self.subdir = subdir

        Component.__init__(self, fs, server, enabled)
        self.mtpt = None
        self.proc_states = {}

    @property
    def fspath(self):
        """
        Return the full filesystem name needed to mount this client
        """
        if self.subdir:
            return '/'.join((self.fs.fs_name, self.subdir.lstrip('/')))
        else:
            return self.fs.fs_name

    def longtext(self):
        """
        Return the client filesystem name and mount point.
        """
        return "%s on %s" % (self.fspath, self.mount_path)

    def uniqueid(self):
        """
        Return a unique string representing this client.

        This takes self.mount_path in account.
        """
        return "%s-%s" % (Component.uniqueid(self), self.mount_path)

    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        Component.update(self, other)
        self.mount_path = other.mount_path

        # Compat v0.910: Following values depend on Shine remote version
        self.mount_options = getattr(other, 'mount_options', None)
        self.mtpt = getattr(other, 'mtpt', getattr(other, 'status_info', None))
        self.proc_states = getattr(other, 'proc_states', {})
        self.subdir = getattr(other, 'subdir', None)

    def lustre_check(self):
        """
        Check Client health at Lustre level.
        """

        self.state = None   # Undefined

        proc_lov_match = glob("/proc/fs/lustre/lov/%s-clilov-*" %
                              self.fs.fs_name)

        if not proc_lov_match:
            self.state = OFFLINE
            return

        #
        # There is at least one clilov declared. Check for coherence.
        #
        loaded = os.path.isdir(proc_lov_match[0])

        # check for presence in /proc/mounts
        f_proc_mounts = open("/proc/mounts", 'r')
        try:
            curr_lnetdev = None
            for line in f_proc_mounts:
                if line.find(" %s lustre " % self.mount_path) > 0:
                    lnetdev, mntp = line.split(' ', 2)[0:2]
                    if loaded:
                        curr_lnetdev = lnetdev
                        self.state = MOUNTED
                        self.mtpt = mntp
                    else:
                        self.state = CLIENT_ERROR
                        if lnetdev != curr_lnetdev:
                            raise ComponentError(self, "conflicting mounts "
                                                "detected for %s and %s on %s" %
                                                 (lnetdev, curr_lnetdev,
                                                  self.mount_path))
                        else:
                            raise ComponentError(self, "multiple mounts "
                                                 "detected for %s (%s)" %
                                                 (lnetdev, self.mount_path))
        finally:
            f_proc_mounts.close()

        if loaded and self.state != MOUNTED:
            # up but not mounted = incoherent state
            self.state = CLIENT_ERROR
            raise ComponentError(self, "incoherent client state for FS '%s'"
                                       " (not mounted but loaded. Mount in "
                                       "progress?)" % self.fs.fs_name)

        # Look for some evictions
        self._lustre_check_proc_state()


    def _lustre_check_proc_state(self):
        """Check current target status in /proc/fs/lustre/*/*/state"""

        self.proc_states = {}
        for entry in glob("/proc/fs/lustre/??c/%s-*/state" % self.fs.fs_name):
            f_state = open(entry, 'r')
            for line in f_state:
                if line.startswith('current_state:'):
                    state_name = line.split(None, 1)[1].strip()

                    # Ignore inactive targets
                    if state_name != 'FULL':
                        mo = re.search(r'/(%s-\w{3}[0-9a-fA-F]{4})-' %
                                       self.fs.fs_name, entry)
                        try:
                            if not self.fs.components[mo.group(1)].is_active():
                                break
                        except (AttributeError, KeyError):
                            pass

                    self.proc_states.setdefault(state_name, 0)
                    self.proc_states[state_name] += 1
                    # Stop reading other file lines
                    break
            f_state.close()

        if 'EVICTED' in self.proc_states:
            self.state = CLIENT_ERROR
            raise ComponentError(self, 'client connection error (%d evictions)'
                                       %  self.proc_states['EVICTED'])

    def text_status(self):
        """
        Return a human text form for the client state, displaying the various
        connection states if there are not FULL.
        """

        text = Component.text_status(self)
        states = []
        for state, total in self.proc_states.items():
            if state != 'FULL':
                states.append("%s=%d" % (state.lower(), total))
        if states:
            text += ' (%s)' % ' '.join(states)

        return text


    #
    # Client actions
    #

    def mount(self, **kwargs):
        """Mount a Lustre client."""
        return StartClient(self, **kwargs)

    def umount(self, **kwargs):
        """Umount a Lustre client."""
        return StopClient(self, **kwargs)
