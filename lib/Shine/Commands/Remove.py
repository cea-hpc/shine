# Remove.py -- File system removing commands
# Copyright (C) 2007, 2008 BULL S.A.S
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

# Import Section

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *

# Command base class
from Base.RemoteCommand import RemoteCriticalCommand
from Base.CommandRCDefs import *
from Base.Support.FS import FS
from Base.Support.Nodes import Nodes

# Error handling
from Exceptions import *

# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler

# Command helper
from Shine.FSUtils import open_lustrefs

# Lustre events and errors
import Shine.Lustre.EventHandler
from Shine.Lustre.Disk import *
from Shine.Lustre.FileSystem import *


class GlobalRemoveEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self):
        pass

class Remove(RemoteCriticalCommand):
    """
    This Remove Command object is used to completly remove the
    File System description from the Shine environment.
    All datas are lost after the Remove command completion.
    """
    
    def __init__(self):
        """
        Initialization of the Remove command object
        """
        # Call parent intialization function
        RemoteCriticalCommand.__init__(self)
        self.fs_support = FS(self, optional=False)

    def get_name(self):
        """
        Return the name of the command.
        """
        return "remove"

    def get_desc(self):
        """
        Return the description message of the command.
        """
        return "Remove a previously installed file system"

    target_status_rc_map = { \
            MOUNTED : RC_FAILURE,
            RECOVERING : RC_FAILURE,
            OFFLINE : RC_OK,
            TARGET_ERROR : RC_TARGET_ERROR,
            CLIENT_ERROR : RC_CLIENT_ERROR,
            RUNTIME_ERROR : RC_RUNTIME_ERROR }

    def fs_status_to_rc(self, status):
        return self.target_status_rc_map[status]

    def execute(self):
        result = RC_OK

        self.init_execute()

        # Do not allow implicit filesystems format.
        if not self.opt_f:
            raise CommandHelpException(\
                    "Missing -f option. You must specify at least one file system name.", self)

        # Walk through the list of File system name provided by the user
        for fsname in self.fs_support.iter_fsname():
            # Install appropriate event handler.
            eh = self.install_eventhandler(None, GlobalRemoveEventHandler())

            # Open configuration and instantiate a Lustre FS.
            fs_conf, fs = open_lustrefs(fsname, None,
                    nodes=self.nodes_support.get_nodeset(),
                    indexes=None,
                    event_handler=eh)

            # Prepare options...
            fs.set_debug(self.debug_support.has_debug())

            # Get first the status of any FS components
            statusdict = fs.status(STATUS_ANY)

            if not self.has_local_flag():

                status_info = None
                if MOUNTED in statusdict or RECOVERING in statusdict:
                    # mounted filesystem!
                    status_info = "WARNING: Filesystem %s is started!" % fs.fs_name

                if RUNTIME_ERROR in statusdict:
                    # wont be able to remove on these nodes
                    status_info = "WARNING: Removing %s might failed on some nodes (see above)!" % fs.fs_name
                    for nodes, msg in fs.proxy_errors:
                        print nodes
                        print '-' * 15
                        print msg

                if status_info:
                    print status_info

                if self.ask_confirm("Please confirm the removal of filesystem ``%s''" % fs.fs_name):
                    print "Removing filesystem %s..." % fs.fs_name
                    rc = fs.remove()
                    if rc:
                        print "Error: failed to remove all filesystem %s configuration files" % fs.fs_name
                        result = RC_FAILURE

                    print "Unregistering FS %s from backend..." % fs.fs_name
                    rc = self.unregister_fs(fs_conf)
                    if rc:
                        print "Error: failed to unregister FS from backend (rc=%d)" % rc
                    else:
                        print "Filesystem %s removed." % fs.fs_name
                else:
                    result = RC_FAILURE

            elif self.remote_call:
                rc = fs.remove()
                if rc:
                    result = RC_FAILURE
        
        return result

    def unregister_fs(self, fs_conf):
        # Retrieve the list of file system client
        client_status_dict = fs_conf.get_status_clients()

        # If there is some client for this file system we have to
        # unregister each of them from the backend
        if not client_status_dict == None:
            nodes = NodeSet()
            
            for node in client_status_dict.keys():
                nodes.add(node)
                
            # Unregister all the file system client
            fs_conf.unregister_clients(nodes)

        # Unregister file system configuration from the backend
        fs_conf.unregister_fs()

