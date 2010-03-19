# Client.py -- Lustre Client
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

import glob
import os 

from Shine.Lustre.Actions.StartClient import StartClient
from Shine.Lustre.Actions.StopClient import StopClient

from Shine.Lustre.Server import Server
from Shine.Lustre.Target import MOUNTED, OFFLINE, INPROGRESS, CLIENT_ERROR, RUNTIME_ERROR

#
# Text form for different client states. 
#
# Could be nearly merged with Target state_text_map if MOUNTED value
# becomes the same.
state_text_map = { 
    None: "unknown",
    OFFLINE: "offline", 
    CLIENT_ERROR: "ERROR", 
    MOUNTED: "mounted", 
    RUNTIME_ERROR: "CHECK FAILURE" 
}

class ClientException(Exception):
    def __init__(self, client, message=None):
        Exception.__init__(self, message)
        self.client = client

class ClientError(ClientException):
    """
    Client error exception.
    """


class Client:

    def __init__(self, fs, server, mount_path, enabled=True):
        """
        Initialize a Lustre client object.
        """

        ### Not serializable

        # attached file system
        self.fs = fs

        ### Serializable
        assert isinstance(server, Server)
        self.server = server
        self.mount_path = mount_path
        self.action_enabled = enabled

        self.state = None   # Unknown
        self.status_info = None

        self.fs._attach_client(self)

    def match(self, other):
        return self.server in other.server

    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        self.mount_path = other.mount_path
        self.state = other.state
        self.status_info = other.status_info

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['fs']
        return odict

    def __setstate__(self, dict):
        self.__dict__.update(dict)
        self.fs = None

    def text_status(self):
        """
        Return a human text form for the client state.
        """
        return state_text_map.get(self.state, "BUG STATE %d" % self.state)

    def _lustre_check(self):
        """
        Lustre client state check.
        """

        self.state = None   # Undefined

        proc_lov_match = glob.glob("/proc/fs/lustre/lov/%s-clilov-*" % self.fs.fs_name)

        if len(proc_lov_match) == 0:
            self.state = OFFLINE
        else:
            loaded = False
            proc_lov = proc_lov_match[0]
            if os.path.isdir(proc_lov):
                loaded = True

            # check for presence in /proc/mounts
            f_proc_mounts = open("/proc/mounts", 'r')
            try:
                for line in f_proc_mounts:
                    if line.find(" %s lustre " % self.mount_path) > 0:
                        lnetdev, mntp = line.split(' ', 2)[0:2]
                        if loaded:
                            self.lnetdev = lnetdev
                            self.state = MOUNTED
                            self.status_info = "%s" % mntp
                        else:
                            self.state = CLIENT_ERROR
                            if lnetdev != self.lnetdev:
                                raise ClientError(self, "conflicting mounts detected for %s and %s on %s" % \
                                        (lnetdev, self.lnetdev, self.mount_path))
                            else:
                                raise ClientError(self, "multiple mounts detected for %s (%s)" % \
                                        (lnetdev, self.mount_path))
            finally:
                f_proc_mounts.close()

            if loaded and self.state != MOUNTED:
                # up but not mounted = incoherent state
                self.state = CLIENT_ERROR
                raise ClientError(self, "incoherent client state for FS '%s' (not mounted but still loaded)" % \
                        self.fs.fs_name)

    def _action_start(self, act):
        """Called by Actions.* when starting"""
        self.fs._invoke('ev_%s%s_start' % (act, 'client'), client=self)

    def _action_done(self, act):
        """Called by Actions.* when done"""
        self.fs._invoke('ev_%s%s_done' % (act, 'client'), client=self)

    def _action_timeout(self, act):
        """Called by Actions.* on timeout"""
        self.fs._invoke('ev_%s_timeout' % (act, 'client'), client=self)

    def _action_failed(self, act, rc, message):
        """Called by Actions.* on failure"""
        self.fs._invoke('ev_%s%s_failed' % (act, 'client'), client=self, rc=rc, message=message)


    def status(self):
        """
        Check client status.
        """
        self._action_start('status')

        try:
            self._lustre_check()
        except ClientError, e:
            self._action_failed('status', rc=None, message=str(e))

        self._action_done('status')

    def start(self, **kwargs):
        """
        Start Lustre client.
        """

        self._action_start('start')

        try:
            self._lustre_check()
            if self.state == MOUNTED:
                self.status_info = "%s is already mounted on %s" % (self.fs.fs_name, self.status_info)
                self._action_done('start')
            else:
                action = StartClient(self, **kwargs)
                action.launch()

        except ClientError, e:
            self._action_failed('start', rc=None, message=str(e))

    def stop(self, **kwargs):
        """
        Stop Lustre client.
        """

        self._action_start('stop')

        try:
            self._lustre_check()
            if self.state == OFFLINE:
                self.status_info = "%s is not mounted" % (self.fs.fs_name)
                self._action_done('stop')
            else:
                action = StopClient(self, **kwargs)
                action.launch()

        except ClientError, e:
            self._action_failed('stop', rc=None, message=str(e))

