# Target.py -- Lustre Target base class
# Copyright (C) 2007-2013 CEA
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

import os
import stat
from glob import glob

from ClusterShell.NodeSet import NodeSet

from Shine.Lustre.Actions.Devices import StartDevice, StopDevice
from Shine.Lustre.Actions.Format import Format, Tunefs, JournalFormat
from Shine.Lustre.Actions.StartTarget import StartTarget
from Shine.Lustre.Actions.StopTarget import StopTarget
from Shine.Lustre.Actions.Fsck import Fsck

from Shine.Lustre.Disk import Disk, DiskDeviceError, DiskNoDeviceException
from Shine.Lustre.Component import Component, ComponentError, \
                                   MOUNTED, EXTERNAL, RECOVERING, OFFLINE, \
                                   TARGET_ERROR, RUNTIME_ERROR, INACTIVE, \
                                   MIGRATED, NO_DEVICE
from Shine.Lustre.Server import Server, ServerGroup
from operator import itemgetter
from itertools import groupby


class Target(Component, Disk):

    #
    # Text form for different client states. 
    #
    # Could be nearly merged with Target state_text_map if MOUNTED value
    # becomes the same.
    STATE_TEXT_MAP = { 
        None:          "unknown",
        EXTERNAL:      "external", 
        RECOVERING:    "recovering", 
        OFFLINE:       "offline", 
        TARGET_ERROR:  "ERROR", 
        MOUNTED:       "online", 
        RUNTIME_ERROR: "CHECK FAILURE",
        INACTIVE:      "inactive",
        MIGRATED:      "migrated",
        NO_DEVICE:     "no_device"
    }

    def __init__(self, fs, server, index, dev, jdev=None, group=None,
            tag=None, enabled=True, mode='managed', network=None,
            active='yes', dev_run_action=None):
        """
        Initialize a Lustre target object.
        """
        Disk.__init__(self, dev)
        self._states = {}
        Component.__init__(self, fs, server, enabled, mode, active)

        self.defaultserver = server      # Default server the target runs on
        self.failservers = ServerGroup() # All failover servers

        assert index is not None
        self.index = int(index)
        self.group = group
        self.tag = tag
        self.network = network
        self.mntdev = self.dev
        self.recov_info = None

        if jdev:
            self.journal = Journal(self, jdev)
        else:
            self.journal = None

        self.dev_run_action = dev_run_action

        # If target mode is external then set target state accordingly
        if self.is_external():
            self.state = EXTERNAL

        # If target is inactive, then set target state accordingly
        if not self.is_active():
            self.state = INACTIVE

    @property
    def label(self):
        """Return the target label which match the Lustre target name."""
        return "%s-%s%04x" % (self.fs.fs_name, self.TYPE.upper(), self.index)

    def __lt__(self, other):
        return self.START_ORDER < other.START_ORDER

    def uniqueid(self):
        """
        Return a unique string representing this target.

        This matches the Target label.
        """
        # uniqueid is used when the target is added to a filesystem.
        # We cannot use the target servers list because it can changed when
        # add_server() is called.
        return self.label

    def get_state(self):
        """Compute target global state based on remote nodes results."""
        # Group target's remote nodes statuses by state.
        sdict = {}
        sorted_states = sorted(self._states.iteritems(), key=itemgetter(1))
        for state, nodes in groupby(sorted_states, key=itemgetter(1)):
            sdict[state] = map(itemgetter(0), nodes)

        if None in sdict and len(sdict[None]) == len(self._states):
            return None

        elif INACTIVE in sdict:
            return INACTIVE

        elif MOUNTED in sdict:
            if len(sdict[MOUNTED]) > 1 or RECOVERING in sdict:
                return TARGET_ERROR
            elif str(self.defaultserver.hostname) in sdict[MOUNTED]:
                return MOUNTED
            else:
                return MIGRATED

        elif RECOVERING in sdict:
            if len(sdict[RECOVERING]) > 1 or MOUNTED in sdict:
                return TARGET_ERROR
            else:
                return RECOVERING

        elif OFFLINE in sdict:
            return OFFLINE

        elif TARGET_ERROR in sdict:
            return TARGET_ERROR

        elif RUNTIME_ERROR in sdict:
            return RUNTIME_ERROR

        elif NO_DEVICE in sdict:
            return NO_DEVICE

    def set_state(self, value):
        """Update target state on the current node."""
        self._states[str(self.server.hostname)] = value

    state = property(get_state, set_state)

    def get_local_state(self):
        """Get local server's target state."""
        if self.fs.local_server is None:
            return None

        return self._states[str(self.fs.local_server.hostname)]

    def set_local_state(self, value):
        """Set local server's target state."""
        if self.fs.local_server is not None:
            self._states[str(self.fs.local_server.hostname)] = value

    local_state = property(get_local_state, set_local_state)

    def sanitize_state(self, nodes=None):
        """
        Clean component state if it is wrong.
        """
        for nodename in nodes:
            if self._states[nodename] is None:
                self._states[nodename] = RUNTIME_ERROR

    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        Disk.update(self, other)
        # We used to call Component.update(). Be careful if it is updated.
        srvname = str(other.server.hostname)
        self._states[srvname] = other._states[srvname]
        if self._states[srvname] == RECOVERING:
            # Compat v0.910: 'recov_info' value depends on remote version
            self.recov_info = getattr(other, 'recov_info',
                                      getattr(other, 'status_info', None))
        self.index = other.index

        # other could be a pre shine 1.5 object, in this case, let's report it.
        if getattr(other, '_compat', False) is True:
            msg = "WARNING: shine version mismatch !!!\n" \
                  "\tPartial results may show up.\n" \
                  "\tMigrated targets may not be detected.\n" \
                  "\tTo avoid this, please synchronize shine versions."
            self.fs._handle_shine_proxy_error(srvname, msg)

    def add_server(self, server):
        assert isinstance(server, Server)
        self.failservers.append(server)
        self._states[str(server.hostname)] = None

    def update_server(self):
        """
        Compute and set component's server based on remote nodes results.
        If the component is started, server is the one on which it is started.
        If the component is stopped or on error, server is the default server.
        Returns False if target is started twice, True in all other cases.
        """
        srvname = None

        servers = [srv for srv, state in self._states.iteritems()
                   if state in (MOUNTED, RECOVERING)]
        if len(servers) > 1:
            return False
        elif len(servers) == 1:
            srvname = servers[0]
        else:
            servers = [srv for srv, state in self._states.iteritems()
                       if state is not None]
            if len(servers) == 1:
                srvname = servers[0]


        if srvname is not None:
            self.server = self.allservers().select(NodeSet(srvname))[0]

        return True

    def allservers(self):
        """
        Return all servers this target can run on.
        The default server is the first element, then all possible failover servers.
        """
        #XXX: This method could be possibly dropped if the code in Status
        #     command is optimized.
        grp = ServerGroup([self.defaultserver])
        for srv in self.failservers:
            grp.append(srv)
        return grp

    def failover(self, candidates):
        """
        Helper method to change Target current server based on a candidate list.

        It checks if only one server from the candidate list matches one of the
        failover server of this target. If more than one matches, it
        raises an exception. If no server matches it returns False. If it has
        changes the current server, it returns true.
        """
        intersec = self.failservers.select(candidates)

        # If we have more than one possible failover nodes, it is ambiguous
        if len(intersec) > 1:
            raise ComponentError(self, "More than one failover server matches.")

        if len(intersec) == 1:
            self.server = intersec[0]
            return True

        return False


    def get_id(self):
        """
        Get target human readable identifier.
        """
        if self.tag is not None:
            return self.tag

        return self.label

    def longtext(self):
        """
        Return the target name and device
        """
        return "%s (%s)" % (self.label, self.dev)

    def get_nids(self):
        """
        Return an ordered list of target's NIDs.
        """
        return [s.nids for s in self.allservers()]

    def text_status(self):
        """
        Return a human text form for the target state.
        """
        state = Component.text_status(self)
        if self.state not in (TARGET_ERROR, RUNTIME_ERROR) and \
           set((RUNTIME_ERROR, TARGET_ERROR)) & set(self._states.values()):
            state += "*"
        if self.state == RECOVERING:
            state += " for %s" % self.recov_info
        return state

    #
    # Target sanity checks
    #

    def full_check(self, mountdata=True):
        """
        Sanity checks for device files and Lustre status.
        If mountdata is set to False, target content will not be analyzed.
        """

        # check for disk level status
        try:
            self._device_check()
            if mountdata:
                self._mountdata_check(self.label)

            if self.journal:
                self.journal.full_check()

        except DiskNoDeviceException, error:
            self.local_state = NO_DEVICE
            return

        except (ComponentError, DiskDeviceError), error:
            self.local_state = TARGET_ERROR
            raise ComponentError(self, str(error))

        # check for Lustre level status
        self.lustre_check()

    def lustre_check(self):
        """
        Check target health at Lustre level.
        """

        self.local_state = None   # Unknown

        # find pathnames matching wanted lustre procfs
        # (Since Lustre 2.4. More than one path could be returned.
        #  The first one is fine.)
        mntdev_path = glob('/proc/fs/lustre/*/%s/mntdev' % self.label)

        recov_path = glob('/proc/fs/lustre/*/%s/recovery_status' % self.label)
        assert len(recov_path) <= 1

        # check for label presence in /proc : is this lustre target started?
        if len(mntdev_path) == 0 and len(recov_path) == 0:
            self.local_state = OFFLINE
        elif len(mntdev_path) == 0:
            self.local_state = TARGET_ERROR
            raise ComponentError(self, "incoherent state in " \
                                       "/proc/fs/lustre for %s" % self.label)
        else:
            # get target's real device
            fproc = open(mntdev_path[0])
            try:
                self.mntdev = fproc.readline().rstrip('\n')
            finally:
                fproc.close()

            loaded = True

            # check for presence in /proc/mounts
            f_proc_mounts = open("/proc/mounts", 'r')
            try:
                for line in f_proc_mounts:
                    if line.find("%s " % self.mntdev) == 0:
                        if line.split(' ', 3)[2] == "lustre":
                            if loaded:
                                self.local_state = MOUNTED
                            else:
                                self.local_state = TARGET_ERROR
                                raise ComponentError(self, "multiple " \
                                        " mounts detected for %s" % self.label)
            finally:
                f_proc_mounts.close()

            if self.local_state != MOUNTED and loaded:
                self.local_state = TARGET_ERROR
                # up but not mounted = incoherent state
                # check for loaded state: ST, UP...
                raise ComponentError(self, "incoherent state for %s " \
                                     "(started but not mounted?)" % self.label)

            if self.local_state == MOUNTED and not loaded:
                self.local_state = TARGET_ERROR
                # mounted but not up = incoherent state
                # /etc/fstab was not correctly cleaned
                raise ComponentError(self, "incoherent state for %s " \
                                     "(mounted but not started?)" % self.label)

            if self.local_state == MOUNTED and self.TYPE != MGT.TYPE:
                # check for MDT or OST recovery (MGS doesn't make any recovery)
                try:
                    fproc = open(recov_path[0], 'r')
                except (IOError, IndexError):
                    self.local_state = TARGET_ERROR
                    raise ComponentError(self, "recovery_state file not " \
                                                  "found for %s" % self.label)

                try:

                    for line in fproc:
                        if line.startswith("status:"):
                            status = line.rstrip().split(' ', 2)[1]
                            break

#
# Recovering information depends on Lustre version.
#
# VERSION:                2.0            1.8                     1.6
#
# connected_clients:  connect/TOTAL   connect/TOTAL            connect/TOTAL
# req_replay:         req_replay      ---                      ---
# lock_repay:         lock_replay     ---                      ---
# delayed_client:     ---             delay/TOTAL              ---
# completed_clients:  connect-replay  TOTAL-recov-delay/TOTAL  TOTAL-recov/TOTAL
# evicted_clients:    stale           ---                      ---
#
                    if status == "RECOVERING":
                        time_remaining = "??"
                        completed = -1
                        evicted = 0
                        total = 0
                        for line in fproc:
                            line = line.strip()
                            if line.startswith("time_remaining:"):
                                time_remaining = line.split(' ', 1)[1]
                            elif line.startswith("connected_clients:"):
                                total = int(line.split('/', 1)[1])
                            elif line.startswith("evicted_clients:"):
                                evicted = int(line.split(' ', 1)[1])
                            elif line.startswith("completed_clients:"):
                                completed = line.split(' ', 1)[1]
                                completed = int(completed.split('/', 1)[0])
                        self.local_state = RECOVERING
                        self.recov_info = "%ss (%s/%s)" % (time_remaining,
                                                    completed + evicted, total)
                finally:
                    fproc.close()

    #
    # Helper methods to check component state in Actions.
    #

    def is_started(self):
        """Return True if the target device is mounted."""
        return self.local_state in (MOUNTED, RECOVERING)

    def raise_if_started(self, message):
        """Raise a ComponentError if the target device is mounted."""
        if self.local_state != OFFLINE:
            if self.is_started():
                reason = "%s: target %s (%s) is started"
            else:
                reason = "%s: target %s (%s) is busy"
            self.local_state = TARGET_ERROR
            raise ComponentError(self, reason % (message, self.label, self.dev))

    #
    # Target actions
    #

    def format(self, **kwargs):
        """
        Check the target is correct and not used and format it in Lustre
        format.
        """
        action = Format(self, **kwargs)

        if self.journal:
            jaction = JournalFormat(self.journal, **kwargs)
            action.depends_on(jaction)
        else:
            jaction = None

        if self.dev_run_action:
            if jaction:
                jaction.depends_on(StartDevice(self, **kwargs))
            else:
                action.depends_on(StartDevice(self, **kwargs))

        return action

    def tunefs(self, **kwargs):
        """
        Apply all on-disk metadata using Target description and tunefs.lustre
        command.
        """
        return Tunefs(self, **kwargs)

    def fsck(self, **kwargs):
        """
        Apply a filesystem coherency check on the Target. This does not
        check coherency between several targets.
        """
        return Fsck(self, **kwargs)

    def start(self, **kwargs):
        """Start the local Target and check for system sanity."""
        action = StartTarget(self, **kwargs)
        if self.dev_run_action:
            action.depends_on(StartDevice(self, **kwargs))
        return action

    def stop(self, **kwargs):
        """Stop the local Target and check for system sanity."""
        stop_target = StopTarget(self, **kwargs)
        if self.dev_run_action:
            action = StopDevice(self, **kwargs)
            action.depends_on(stop_target)
            return action
        return stop_target

    def __setstate__(self, state):
        """
        Enforce pickle backward compatibility with older servers.
        Before shine 1.5, Target objects have a inherited 'state' attribute
        and no '_states' dictionary.
        Begining with shine 1.5, Target objects have a '_states' dictionary
        and a 'state' property (forbidding access to the inherited
        'state' attribute)
        """
        self.__dict__.update(state)
        if not hasattr(self, '_states'):
            # Remote object is a pre shine 1.5 object.
            # Create and initialize new style _states attribute.
            setattr(self, '_states',
                    {str(self.server.hostname): state['state']})

            # Add this flag to be able to later notify user of this.
            setattr(self, '_compat', True)

class MGT(Target):

    TYPE = 'mgt'
    START_ORDER = 2
    DISPLAY_ORDER = 2

    @property
    def label(self):
        """Always returns the MGS label which is 'MGS'."""
        return 'MGS'

class MDT(Target):

    TYPE = 'mdt'
    # START_ORDER needs to have OST class declared.
    # See value below.
    DISPLAY_ORDER = MGT.DISPLAY_ORDER + 1


class OST(Target):

    TYPE = 'ost'
    START_ORDER = MGT.START_ORDER + 1
    DISPLAY_ORDER = MDT.DISPLAY_ORDER + 1

# This is declared here due to cycling-dependencies.
# See MDT class.
MDT.START_ORDER = OST.START_ORDER + 1

class Journal(Component):
    """
    Manage a target external journal device.
    """

    TYPE = 'journal'

    def __init__(self, target, device):
        Component.__init__(self, target.fs, target.server,
                           target.action_enabled, target._mode)
        self.target = target
        self.dev = device

    @property
    def label(self):
        return self.uniqueid()

    def uniqueid(self):
        return "%s_jdev" % self.target.uniqueid()

    def longtext(self):
        return "%s journal (%s)" % (self.target.get_id(), self.dev)

    def full_check(self, mountdata=True):
        """Device type check."""

        try:
            info = os.stat(self.dev)
        except OSError, exp:
            raise ComponentError(self, str(exp))

        if not stat.S_ISBLK(info[stat.ST_MODE]):
            raise ComponentError(self, "bad journal device")

    def lustre_check(self):
        pass
