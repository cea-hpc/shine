# LMF.py -- Impl. class to deal with LMF option
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

from Shine.Configuration.Globals import Globals 

import os.path

class LMF:
    """
    Lustre Model File command parameter support.
    """
    
    def __init__(self, cmd):

        attr = { 'optional' : False,
                 'hidden' : False,
                 'doc' : "path of the Lustre Model File" }

        self.cmd = cmd
        self.cmd.add_option('m', "LMF file path", attr)

    
    def get_lmf_path(self):
        """
        Return the LMF file path. Perform some basic checks and add (if needed)
        the path of the base directory.
        """
        # First check if a file exists at the specified location, if so, just
        # return it.
        if os.path.isfile(self.cmd.opt_m):
            return self.cmd.opt_m
        # If not, check for configuration's default LMF directory.
        lmf_dir = Globals().get_lmf_dir()
        if not os.path.isabs(self.cmd.opt_m) and os.path.isdir(lmf_dir):
            # Directory path is valid, add supposed LMF file.
            file_path = os.path.join(lmf_dir, self.cmd.opt_m)
            if os.path.isfile(file_path):
                return file_path
            else:
                # At last, check for missing extension.
                f_name, f_ext = os.path.splitext(self.cmd.opt_m)
                if not f_ext:
                    file_path = os.path.join(lmf_dir, "%s.lmf" % f_name) 
                    if os.path.isfile(file_path):
                        return file_path
        # Failed
        return None


