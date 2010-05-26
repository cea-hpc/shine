# Target.py -- Lustre Target base class
# Copyright (C) 2007, 2008 CEA
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

from ClusterShell.Task import task_self
from ClusterShell.NodeSet import NodeSet

from Shine.Lustre.Actions.Format import Format
from Shine.Lustre.Actions.StartTarget import StartTarget
from Shine.Lustre.Actions.StopTarget import StopTarget
from Shine.Lustre.Actions.Fsck import Fsck

from Shine.Lustre.Disk import Disk, DiskDeviceError
from Shine.Lustre.Component import Component, MOUNTED, EXTERNAL, RECOVERING, OFFLINE, INPROGRESS, TARGET_ERROR, RUNTIME_ERROR
from Shine.Lustre.Server import Server


class TargetError(Exception):
    """
    Target related error occured.
    """
    def __init__(self, target, message):
        self.target = target
        self.message = message

    def __str__(self):
        return self.message

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
            tag=None, enabled=True, mode='managed'):
        """
        Initialize a Lustre target object.
        """
        Component.__init__(self, fs, server, enabled, mode)
        Disk.__init__(self, dev, jdev)

        self.defaultserver = server   # Default server the target runs on
        self.failservers = [ ]        # All failover servers

        assert index is not None
        self.index = int(index)
        self.group = group
        self.tag = tag

        # If target mode is external then set target state accordingly
        if self.is_external():
            self.state = EXTERNAL

    @property
    def label(self):
        """Return the target label which match the Lustre target name."""
        return "%s-%s%04x" % (self.fs.fs_name, self.TYPE.upper(), self.index)


    def __lt__(self, other):
        return self.START_ORDER < other.START_ORDER

    def match(self, other):
        return Component.match(self, other) and \
               self.dev == other.dev and \
               self.index == other.index and \
               str(self.defaultserver) == str(other.defaultserver)

    def update(self, other):
        """
        Update my serializable fields from other/distant object.
        """
        Disk.update(self, other)
        Component.update(self, other)
        self.index = other.index

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
        return [self.defaultserver] + self.failservers

    def failover(self, candidates):
        """
        Helper method to change Target current server based on a candidate list.

        It checks if only one server from the candidate list matches 
        one of the failover server of this target. If more than one matches, it
        raises an exception. If no server matches if retun False. If it has
        changes the current server, it returns true.
        """
        intersec = candidates.intersection(NodeSet.fromlist(self.failservers))

        # If we have more than one possible failover nodes, it is ambiguous
        if len(intersec) > 1:
            raise TargetError(self, "More than one failover server matches.")

        if len(intersec) == 1:
            # XXX: We need to find intersec[0] in failservers.. we can do
            # something better here...
            for srv in self.failservers:
                 if intersec[0].__eq__(srv):
                    self.server = srv
                    break
            return True

        return False


    def get_id(self):
        """
        Get target human readable identifier.
        """
        if self.tag is not None:
            return self.tag

        return self.label
    
    def get_nids(self):
        """
        Return an ordered list of target's NIDs.
        """
        return [s.nid for s in self.allservers()]

    def text_status(self):
        """
        Return a human text form for the target state.
        """
        if self.state == RECOVERING:
            return "%s for %s" % (self.STATE_TEXT_MAP.get(RECOVERING), self.status_info)
        else:
            return Component.text_status(self)

    def _lustre_check(self):

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
            raise TargetDeviceError(self, "incoherent state in /proc/fs/lustre for %s" % \
                    self.label)
        else:
            # get target's real device
            f = open(mntdev_path[0])
            try:
                self.mntdev = f.readline().rstrip('\n')
            finally:
                f.close()

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
                                raise TargetDeviceError(self, "multiple mounts detected for %s" % \
                                        self.label)
            finally:
                f_proc_mounts.close()

            if self.state != MOUNTED and loaded:
                self.state = TARGET_ERROR
                # up but not mounted = incoherent state
                # check for loaded state: ST, UP...
                raise TargetDeviceError(self, "incoherent state for %s (started but not mounted?)" % \
                       self.label)

            if self.state == MOUNTED and self.TYPE != 'mgt':
                # check for MDT or OST recovery (MGS doesn't make any recovery)
                try:
                    f = open(recov_path[0], 'r')
                except (IOError, IndexError):
                    self.state = TARGET_ERROR
                    raise TargetDeviceError(self, "recovery_state file not found for %s" % \
                            self.label)

                try:
                    recovery_duration = -1
                    completed_clients = -1
                    time_remaining = -1

                    for line in f:
                        if line.startswith("status:"):
                            key, status = line.rstrip().split(' ', 2)
                            break
                    if status == "COMPLETE":
                        for line in f:
                            if line.startswith("recovery_duration:"):
                                key, recovery_duration = line.rstrip().split(' ', 2) 
                            if line.startswith("completed_clients:"):
                                key, completed_clients = line.rstrip().split(' ', 2)
                    if status == "RECOVERING":
                        for line in f:
                            if line.startswith("time_remaining:"):
                                key, time_remaining = line.rstrip().split(' ', 2)
                            if line.startswith("completed_clients:"):
                                key, completed_clients = line.rstrip().split(' ', 2)
                        self.state = RECOVERING
                        self.status_info = "%ss (%s)" % (time_remaining, completed_clients)
                finally:
                    f.close()

    def format(self, **kwargs):

        self.state = INPROGRESS
        self._action_start('format')

        try:
            self._device_check()
        except DiskDeviceError, e:
            self.state = TARGET_ERROR
            self._action_failed('format', rc=1, message=str(e))
            return

        try:
            self._lustre_check()

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

        except TargetDeviceError, e:
            self._action_failed('format', rc=-1, message=str(e))

    def fsck(self, **kwargs):

        self.state = INPROGRESS
        self._action_start('fsck')

        try:
            self._device_check()
        except DiskDeviceError, e:
            self.state = TARGET_ERROR
            self._action_failed('fsck', rc=1, message=str(e))
            return

        try:
            self._lustre_check()

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

        except TargetDeviceError, e:
            self._action_failed('fsck', rc=-1, message=str(e))

    def status(self):
        """
        Check target status.
        """
        self._action_start('status')

        try:
            # check for disk level status
            self._disk_check(self.fs.fs_name, self.label)
        except DiskDeviceError, e:
            self.state = TARGET_ERROR
            self._action_failed('status', rc=1, message=str(e))
            return

        # check for Lustre level status
        self._lustre_check()

        self._action_done('status')

    def start(self, **kwargs):

        self.state = INPROGRESS
        self._action_start('start')

        try:
            self._device_check()
            self._lustre_check()

            if self.state != OFFLINE:
                # already mounted ?
                if  self.state == RECOVERING or self.state == MOUNTED:
                    self.status_info = "%s is already started" % self.label
                    self._action_done('start')
                    return
                raise TargetDeviceError(self, "bad state `%s' for %s" % \
                        (self.state, self.label))

            # LBUG #18624
            if not self.dev_isblk:
                task_self().set_info("fanout", 1)

            action = StartTarget(self, **kwargs)
            action.launch()

        except TargetDeviceError, e:
            self._action_failed('start', rc=None, message=str(e))

    def stop(self, **kwargs):

        self.state = INPROGRESS
        self._action_start('stop')

        try:
            self._disk_check()
            self._lustre_check()

            if self.state == OFFLINE:
                self.status_info = "%s is already stopped" % self.label
                self._action_done('stop')
                return

            # LBUG #18624
            if not self.dev_isblk:
                task_self().set_info("fanout", 1)

            action = StopTarget(self, **kwargs)
            action.launch()

        except TargetDeviceError, e:
            self._action_failed('stop', rc=None, message=str(e))

    #
    # Event raising methods
    #

    # Those methods are overload due to the generic name 'target' used.
    # When EventHandlers will be updated and refactorized, check if this is
    # still useful.

    def _action_start(self, act, comp='target'):
        """Called by Actions.* when starting"""
        Component._action_start(self, act, comp)

    def _action_done(self, act, comp='target'):
        """Called by Actions.* when done"""
        Component._action_done(self, act, comp)

    def _action_timeout(self, act, comp='target'):
        """Called by Actions.* on timeout"""
        Component._action_timeout(self, act, comp)

    def _action_failed(self, act, rc, message, comp='target'):
        """Called by Actions.* on failure"""
        Component._action_failed(self, act, comp, rc, message, comp)


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
