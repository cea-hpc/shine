# Edit.py -- Info of file system
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

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *
from Shine.Lustre.FileSystem import FileSystem

from Base.Command import Command
from Base.Support.FS import FS

from Exceptions import *

from errno import *

import getopt
import os
import sys

import fcntl

# ----------------------------------------------------------------------
# * shine edit
# ----------------------------------------------------------------------
class Edit(Command):
    """
    Edit command : allow a wrapped access to shine FS config file which
    add (1) an convenient access and (2) syntax/sanity checking.
    """
    
    def __init__(self):
        Command.__init__(self)

        self.fs_support = FS(self, optional=False)

    def get_name(self):
        return "edit"

    def get_desc(self):
        return "General file system information."

    def execute(self):
        if not self.opt_f:
            print "Error: please specify -f <fsname>"
            sys.exit(1)
        try:
            for fsname in self.fs_support.iter_fsname():

                # Check first if file system is installed
                xmf = "%s/%s.xmf" % (Globals().get_conf_dir(), fsname)
                if not os.path.exists(xmf):
                    raise CommandXMFNotFoundError(fsname)

                editor = None

                # Check the VISUAL environment variable
                e = os.getenv("VISUAL")
                if e:
                    editor = e

                # Check the EDITOR environment variable
                e = os.getenv("EDITOR")
                if e:
                    editor = e

                # Default to vim, vi or nano editor if not specified.
                infile = os.popen("type -p vim || type -p vi || type -p nano")
                
                result = infile.read()
                if result:
                    editor = os.path.normpath(result.strip("\n\r"))
                infile.close()

                if not editor:
                    # Last chance...
                    editor = "/bin/vi"

                # Open editor if file not locked by us.
                f = os.open(xmf, os.O_RDWR)
                r = fcntl.lockf(f, fcntl.LOCK_EX|fcntl.LOCK_NB)
                os.system("%s %s" % (editor, xmf))
                os.close(f)

        except IOError, e:
            if e.errno == EACCES or e.errno == EAGAIN:
                print "shine: %s.xmf file busy (already editing?), try again later" % fsname
            else:
                print "Error: filesystem %s is not installed" % fsname


