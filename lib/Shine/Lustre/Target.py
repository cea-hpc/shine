# Target.py -- Lustre Target base class
# Copyright (C) 2007-2011 CEA
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

import os
import stat
import glob

from ClusterShell.Task import task_self

from Shine.Lustre.Actions.Action import Result
from Shine.Lustre.Actions.Format import Format, Tunefs, JournalFormat
from Shine.Lustre.Actions.StartTarget import StartTarget
from Shine.Lustre.Actions.StopTarget import StopTarget
from Shine.Lustre.Actions.Fsck import Fsck

from Shine.Lustre.Disk import Disk, DiskDeviceError
from Shine.Lustre.Component import Component, ComponentError, \
                                   MOUNTED, EXTERNAL, RECOVERING, OFFLINE, \
                                   INPROGRESS, TARGET_ERROR, RUNTIME_ERROR
from Shine.Lustre.Server import Server, ServerGroup


class TargetError(ComponentError):
    """
    Target related error occured.
    """
    def __init__(self, target, message):
        ComponentError.__init__(self, message)
        self.target = target

class TargetDeviceError(TargetError):
    """
    Target's underlying device error.
    """
    

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
        RUNTIME_ERROR: "CHECK FAILURE" 
    }

    def __init__(self, fs, server, index, dev, jdev=None, group=None,
            tag=None, enabled=True, mode='managed', network=None):
        """
        Initialize a Lustre target object.
        """
        Disk.__init__(self, dev)
        Component.__init__(self, fs, server, enabled, mode)

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

        # If target mode is external then set target state accordingly
        if self.is_external():
            self.state = EXTERNAL

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

    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        Disk.update(self, other)
        Component.update(self, other)
        self.index = other.index

        # Compat v0.910: 'recov_info' value depends on remote version
        self.recov_info = getattr(other, 'recov_info',
                                  getattr(other, 'status_info', None))

    def add_server(self, server):
        assert isinstance(server, Server)
        self.failservers.append(server)

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
            raise TargetError(self, "More than one failover server matches.")

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
        if self.state == RECOVERING:
            return "%s for %s" % (self.STATE_TEXT_MAP.get(RECOVERING),
                                  self.recov_info)
        else:
            return Component.text_status(self)

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
                self._mountdata_check(self.fs.fs_name, self.label)

            if self.journal:
                self.journal.full_check()

        except (JournalError, DiskDeviceError), error:
            self.state = TARGET_ERROR
            raise TargetDeviceError(self, str(error))

        # check for Lustre level status
        self.lustre_check()

    def lustre_check(self):
        """
        Check target health at Lustre level.
        """

        self.state = None   # Unknown

        # find pathnames matching wanted lustre procfs
        mntdev_path = glob.glob('/proc/fs/lustre/*/%s/mntdev' % self.label)
        assert len(mntdev_path) <= 1

        recov_path = glob.glob('/proc/fs/lustre/*/%s/recovery_status' % self.label)
        assert len(recov_path) <= 1

        # check for label presence in /proc : is this lustre target started?
        if len(mntdev_path) == 0 and len(recov_path) == 0:
            self.state = OFFLINE
        elif len(mntdev_path) == 0:
            self.state = TARGET_ERROR
            raise TargetDeviceError(self, "incoherent state in " \
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
                                self.state = MOUNTED
                            else:
                                self.state = TARGET_ERROR
                                raise TargetDeviceError(self, "multiple " \
                                        " mounts detected for %s" % self.label)
            finally:
                f_proc_mounts.close()

            if self.state != MOUNTED and loaded:
                self.state = TARGET_ERROR
                # up but not mounted = incoherent state
                # check for loaded state: ST, UP...
                raise TargetDeviceError(self, "incoherent state for %s " \
                                     "(started but not mounted?)" % self.label)

            if self.state == MOUNTED and not loaded:
                self.state = TARGET_ERROR
                # mounted but not up = incoherent state
                # /etc/fstab was not correctly cleaned
                raise TargetDeviceError(self, "incoherent state for %s " \
                                     "(mounted but not started?)" % self.label)

            if self.state == MOUNTED and self.TYPE != MGT.TYPE:
                # check for MDT or OST recovery (MGS doesn't make any recovery)
                try:
                    fproc = open(recov_path[0], 'r')
                except (IOError, IndexError):
                    self.state = TARGET_ERROR
                    raise TargetDeviceError(self, "recovery_state file not " \
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
                        self.state = RECOVERING
                        self.recov_info = "%ss (%s/%s)" % (time_remaining,
                                                    completed + evicted, total)
                finally:
                    fproc.close()

    def format(self, **kwargs):
        """
        Check the target is correct and not used and format it in Lustre
        format.
        """

        self.state = INPROGRESS
        self._action_start('format')

        try:
            self.full_check(mountdata=False)

            if self.state == OFFLINE:
                # LBUG #18624 : workaround for "multiple mkfs.lustre on loop devices"
                if not self.dev_isblk:
                    # configure one engine client max per task (sequential, bah.)
                    task_self().set_info("fanout", 1)

                self.state = INPROGRESS
                action = Format(self, **kwargs)
                action.launch()
            else:
                # Target state is not DOWN... cannot format device.
                if self.state in [MOUNTED, RECOVERING]:
                    reason = "Cannot format: target %s (%s) is started"
                else:
                    reason = "Cannot format: target %s (%s) is busy"
                self.state = TARGET_ERROR
                raise TargetDeviceError(self, reason % (self.label, self.dev))

        except TargetError, error:
            self._action_failed('format', Result(str(error)))


    def tunefs(self, **kwargs):
        """
        Apply all on-disk metadata using Target description and tunefs.lustre
        command.
        """
        self.state = INPROGRESS
        self._action_start('tunefs')

        try:
            self.full_check()

            if self.state == OFFLINE:
                # LBUG #18624 : workaround for "multiple mkfs.lustre on loop devices"
                if not self.dev_isblk:
                    # configure one engine client max per task (sequential, bah.)
                    task_self().set_info("fanout", 1)

                self.state = INPROGRESS
                Tunefs(self, **kwargs).launch()
            else:
                # Target state is not DOWN... cannot apply tunefs to device.
                if self.state in [MOUNTED, RECOVERING]:
                    reason = "Cannot tunefs: target %s (%s) is started"
                else:
                    reason = "Cannot tunefs: target %s (%s) is busy"
                self.state = TARGET_ERROR
                raise TargetDeviceError(self, reason % (self.label, self.dev))

        except TargetError, error:
            self._action_failed('tunefs', Result(str(error)))


    def fsck(self, **kwargs):
        """
        Apply a filesystem coherency check on the Target. This does not
        check coherency between several targets.
        """

        self.state = INPROGRESS
        self._action_start('fsck')

        try:
            self.full_check(mountdata=False)

            if self.state == OFFLINE:
                self.state = INPROGRESS
                action = Fsck(self, **kwargs)
                action.launch()
            else:
                # Target state is not DOWN... cannot fsck device.
                if self.state in [MOUNTED, RECOVERING]:
                    reason = "Cannot fsck: target %s (%s) is started"
                else:
                    reason = "Cannot fsck: target %s (%s) is busy"
                self.state = TARGET_ERROR
                raise TargetDeviceError(self, reason % (self.label, self.dev))

        except TargetError, error:
            self._action_failed('fsck', Result(str(error)))

    def status(self):
        """
        Check target status.
        """
        self._action_start('status')

        try:
            self.full_check()
            self._action_done('status')
        except TargetError, error:
            self._action_failed('status', Result(str(error)))


    def start(self, **kwargs):
        """
        Start the local Target and check for system sanity.
        """

        self.state = INPROGRESS
        self._action_start('start')

        try:
            self.full_check()

            if self.state != OFFLINE:
                # already mounted ?
                if  self.state == RECOVERING or self.state == MOUNTED:
                    result = Result("%s is already started" % self.label)
                    self._action_done('start', result)
                    return
                raise TargetDeviceError(self, "bad state `%s' for %s" % \
                        (self.state, self.label))

            # LBUG #18624
            if not self.dev_isblk:
                task_self().set_info("fanout", 1)

            action = StartTarget(self, **kwargs)
            action.launch()

        except TargetError, error:
            self._action_failed('start', Result(str(error)))

    def stop(self, **kwargs):
        """
        Stop the local Target and check for system sanity.
        """
        self.state = INPROGRESS
        self._action_start('stop')

        try:
            self.full_check()

            if self.state == OFFLINE:
                result = Result(message="%s is already stopped" % self.label)
                self._action_done('stop', result)
                return

            # LBUG #18624
            if not self.dev_isblk:
                task_self().set_info("fanout", 1)

            action = StopTarget(self, **kwargs)
            action.launch()

        except TargetError, error:
            self._action_failed('stop', Result(str(error)))


class MGT(Target):

    TYPE = 'mgt'
    START_ORDER = 2
    DISPLAY_ORDER = 2

    @property
    def label(self):
        """Always returns the MGS label which is 'MGS'."""
        return 'MGS'

    def _mountdata_check(self, fsname_check=None, label_check=None):
        """Overload Disk method. Do not test filesystem name for MGS."""
        # XXX: As MGT target could be defined as 'external', do we still
        # need to avoid the fsname_check for MGT?
        return Disk._mountdata_check(self, None, label_check)

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

class JournalError(TargetError):
    """Journal target error."""

    def __init__(self, journal, message):
        TargetError.__init__(self, journal.target, message)


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
            raise JournalError(self, str(exp))

        if not stat.S_ISBLK(info[stat.ST_MODE]):
            raise JournalError(self, "bad journal device")

    def lustre_check(self):
        pass

    def format(self, **kwargs):
        """
        Check the journal device is correct and format it to be used as an
        external journal.
        """

        self.state = INPROGRESS
        self._action_start('format')

        try:
            self.full_check()

            self.state = INPROGRESS
            # Warning: kwargs is used to pass 'nextaction'. See JournalFormat.
            action = JournalFormat(self, **kwargs)
            action.launch()

        except JournalError, error:
            self._action_failed('format', Result(str(error)))

