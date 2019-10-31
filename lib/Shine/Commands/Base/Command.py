# Command.py -- Base command class
# Copyright (C) 2007-2015 CEA
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

from __future__ import print_function

import os
import sys

from ClusterShell.NodeSet import NodeSet

from Shine.Configuration.Globals import Globals

from Shine.Lustre.Server import Server

from Shine.Commands.Base.CommandRCDefs import RC_FLAG_RUNTIME_ERROR
from Shine.Commands.Base.RemoteCallEventHandler import RemoteCallEventHandler

# python2/3 compat: raw_input got removed and input behaves differently
try:
    input = raw_input
except NameError:
    pass

class CommandException(Exception):
    """Generic exception for Shine.Commands.Base.Command"""

class CommandHelpException(CommandException):
    """
    Raised when help on this command should be printed.
    """
    def __init__(self, message, cmd):
        CommandException.__init__(self, message)
        self.cmd = cmd


class Command(object):
    """
    The base class for command objects that can be added to the commands
    registry.
    """

    NAME = "<undefined>"
    DESCRIPTION = "Undocumented"
    SUBCOMMANDS = None

    def __init__(self, options=None, args=None):
        self.options = options
        self.arguments = args
        self.params_desc = ""

    def forbidden(self, options, txt):
        if options:
            fulltxt = "'%s' command does not accept %s" % (self.NAME, txt)
            raise CommandHelpException(fulltxt, self)

    def get_params_desc(self):
        pdesc = self.params_desc.strip()
        if self.SUBCOMMANDS:
            return "%s %s" % ('|'.join(self.SUBCOMMANDS), pdesc)
        return pdesc

    def ask_confirm(self, prompt):
        """
        Ask user for confirmation if -y not specified.

        Return True when the user confirms the action, False otherwise.
        """
        if self.options.yes:
            return True

        i = input("%s (y)es/(N)o: " % prompt)
        return i.lower() in ('y', 'yes')

    def filter_rc(self, rc):
        """
        Allow derived classes to filter return codes.
        """
        # default is to not filter return code
        return rc

    def iter_fsname(self):

        # If some labels are specified, they also specifies some fs names.
        # (ie: fsname-OST0000)
        if self.options.labels and not self.options.fsnames:
            self.options.fsnames = []
            for label in self.options.labels:
                fsname = str(label).split('-', 1)[0]
                # Avoid adding the same fs several times
                if fsname not in self.options.fsnames:
                    self.options.fsnames.append(fsname)

        # Build a default filesystem list based on all fs in cache directory.
        elif not self.options.fsnames:
            self.options.fsnames = []
            xmfdir = Globals().get_conf_dir()
            if os.path.isdir(xmfdir):
                for filename in os.listdir(xmfdir):
                    name, ext = os.path.splitext(filename)
                    if name and ext == '.xmf':
                        self.options.fsnames.append(name)

        return iter(self.options.fsnames)

    def get_lmf_path(self):
        """
        Return the LMF file path. Perform some basic checks and add (if needed)
        the path of the base directory.
        """
        # First check if a file exists at the specified location, if so, just
        # return it.
        if os.path.isfile(self.options.model):
            return self.options.model

        # If not, check for configuration's default LMF directory.
        lmf_dir = Globals().get_lmf_dir()
        if not os.path.isabs(self.options.model) and os.path.isdir(lmf_dir):
            # Directory path is valid, add supposed LMF file.
            file_path = os.path.join(lmf_dir, self.options.model)
            if os.path.isfile(file_path):
                return file_path
            else:
                # At last, check for missing extension.
                f_name, f_ext = os.path.splitext(self.options.model)
                if not f_ext:
                    file_path = os.path.join(lmf_dir, "%s.lmf" % f_name)
                    if os.path.isfile(file_path):
                        return file_path
        # Failed
        return None

    def check_valid_list(self, fs_name, fs_nodes, action_txt="do"):
        """
        This helper method verifies, for the provided filesystem, that the
        nodesets possibly set on command line, to restrain the node list, did
        not:
         - disabled all nodes
         - specified nodes which are not in filesystem configuration.
        Return False if nothing was done.
        """

        selected_nodes = self.options.nodes
        excluded_nodes = self.options.excludes

        # Is there unknown host?
        if selected_nodes:
            if excluded_nodes:
                selected_nodes = selected_nodes - excluded_nodes
            if fs_nodes:
                selected_nodes = selected_nodes - fs_nodes
            if selected_nodes:
                print("WARNING: Nothing to %s on %s for `%s'" %
                      (action_txt, selected_nodes, fs_name), file=sys.stderr)

        # All nodes were disabled?
        if len(fs_nodes) == 0:
            print("WARNING: Nothing was done for `%s'." % fs_name,
                  file=sys.stderr)
            return False

        return True

    @classmethod
    def display_proxy_errors(cls, fs):
        """Display proxy error messages for the specified filesystem."""
        for msg, nodes in fs.proxy_errors.walk():
            nodes = str(NodeSet.fromlist(nodes))
            msg = str(msg).replace('THIS_SHINE_HOST', nodes)
            print("%s: %s" % (nodes, msg), file=sys.stderr)

class RemoteCommand(Command):

    def __init__(self, options=None, args=None):
        Command.__init__(self, options, args)
        self.eventhandler = None

    def has_local_flag(self):
        return self.options.local or self.options.remote

    def init_execute(self):
        """
        Initialize execution of remote command, if needed. Should be called
        first from derived classes before really executing the command.
        """
        # Limit the scope of the command if called with local flag (-L) or
        # called remotely (-R).
        if self.has_local_flag():
            self.options.nodes = NodeSet(Server.hostname_short())

    def install_eventhandler(self, local_eventhandler, global_eventhandler):
        """
        Select and install the appropriate event handler.
        """
        if self.options.remote:
            # When called remotely (-R), install a special event handler
            # that knows how to speak the Shine Proxy Protocol using pickle.
            self.eventhandler = RemoteCallEventHandler()
        elif self.options.local:
            self.eventhandler = local_eventhandler
        else:
            self.eventhandler = global_eventhandler
        # return handler for convenience
        return self.eventhandler

    def ask_confirm(self, prompt):
        """
        Ask user for confirmation. Overrides Command.ask_confirm to
        avoid confirmation when called remotely (-R).

        Return True when the user confirms the action, False otherwise.
        """
        return self.options.remote or Command.ask_confirm(self, prompt)

    def filter_rc(self, rc):
        """
        When called remotely, return code are not used to handle shine action
        success or failure, nor for status info. To properly detect ssh or
        remote shine installation failures, we filter the return code here.
        """
        if self.options.remote:
            # Only errors of type RUNTIME ERROR are allowed to go up.
            rc &= RC_FLAG_RUNTIME_ERROR

        return Command.filter_rc(self, rc)
