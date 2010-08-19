# FSLiveCommand.py -- Base commands class : live filesystem
# Copyright (C) 2009 CEA
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

"""
Base class for live filesystem commands (start, stop, status, etc.).
"""

from Shine.Commands.Base.RemoteCommand import RemoteCommand

# Command helper
from Shine.FSUtils import open_lustrefs

# Error handling
from Shine.Commands.Exceptions import CommandHelpException
from Shine.Commands.Base.CommandRCDefs import RC_RUNTIME_ERROR

# Options support classes
from Shine.Commands.Base.Support.FS import FS
from Shine.Commands.Base.Support.Verbose import Verbose
from Shine.Commands.Base.Support.AdditionalOptions import AdditionalOptions
from Shine.Commands.Base.Support.Label import Label
from Shine.Commands.Base.Support.Indexes import Indexes
from Shine.Commands.Base.Support.Target import Target
from Shine.Commands.Base.Support.Yes import Yes

class FSLiveCommand(RemoteCommand):
    """
    shine <cmd> [-f <fsname>] [-n <nodes>] [-dqv]
    """
    
    GLOBAL_EH = None
    LOCAL_EH = None
    
    TARGET_STATUS_RC_MAP = { }

    def __init__(self):
        RemoteCommand.__init__(self)

        self.fs_support = FS(self, optional=True)
        self.verbose_support = Verbose(self)
        self.addopts = AdditionalOptions(self)
        self.label_support = Label(self)

    def fs_status_to_rc(self, status):
        return self.TARGET_STATUS_RC_MAP.get(status, RC_RUNTIME_ERROR)

    def _open_fs(self, fsname, eh):
        fs_conf, fs = open_lustrefs(fsname, None,
            nodes=self.nodes_support.get_nodeset(),
            excluded=self.nodes_support.get_excludes(),
            labels=self.label_support.get_labels(),
            event_handler=eh)
        return fs_conf, fs

    def execute_fs(self, fs, fs_conf, eh, vlevel):
        raise NotImplemented("Derived class must implement.")

    def execute(self):
        result = 0

        self.init_execute()

        # Get verbose level.
        vlevel = self.verbose_support.get_verbose_level()

        # Install appropriate event handler.
        local_eh = None
        global_eh = None
        if self.LOCAL_EH:
            local_eh = self.LOCAL_EH(vlevel)
        if self.GLOBAL_EH:
            global_eh = self.GLOBAL_EH(vlevel)
        eh = self.install_eventhandler(local_eh, global_eh)

        for fsname in self.fs_support.iter_fsname():

            # Open configuration and instantiate a Lustre FS.
            fs_conf, fs = self._open_fs(fsname, eh)

            # Define debuggin level
            fs.set_debug(self.debug_support.has_debug())

            # Eventhandler uses this FS configuration
            if eh:
                eh.fs_conf = fs_conf

            # Run the real job
            result = max(result, self.execute_fs(fs, fs_conf, eh, vlevel))

        return result


class FSTargetLiveCommand(FSLiveCommand):
    """
    Base class for all command dealing with filesystem Target.
    """

    def __init__(self):
        FSLiveCommand.__init__(self)
        self.target_support = Target(self)
        self.indexes_support = Indexes(self)

    def _open_fs(self, fsname, eh):
        fs_conf, fs = open_lustrefs(fsname, 
            self.target_support.get_target(),
            nodes=self.nodes_support.get_nodeset(),
            excluded=self.nodes_support.get_excludes(),
            failover=self.target_support.get_failover(),
            indexes=self.indexes_support.get_rangeset(),
            labels=self.label_support.get_labels(),
            event_handler=eh)
        return fs_conf, fs

class FSTargetLiveCriticalCommand(FSTargetLiveCommand):
    """
    Base class for any command dealing with filesystem Target which require a
    confirmation. This is useful for any critical action we do not want to be
    done automatically, to avoid command line error by example.
    """

    def __init__(self):
        FSTargetLiveCommand.__init__(self)
        self.yes_support = Yes(self)

    def ask_confirm(self, prompt):
        """
        Ask user for confirmation if -y not specified.

        Return True when the user confirms the action, False otherwise.
        """
        return self.yes_support.has_yes() or \
               FSTargetLiveCommand.ask_confirm(self, prompt)
        
    def execute(self):
        # Do not allow implicit filesystems format.
        if not self.opt_f:
            raise CommandHelpException("A filesystem is required (use -f).", self)

        return FSTargetLiveCommand.execute(self)
