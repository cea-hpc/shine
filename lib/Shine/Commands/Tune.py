# Tune.py -- Tune file system
# Copyright (C) 2007 BULL S.A.S
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
from Shine.Configuration.TuningModel import TuningModel
from Shine.Configuration.TuningModel import TuningParameterDeclarationException

from Shine.Lustre.FSLocal import FSLocal
from Shine.Lustre.FSProxy import FSProxy

from Base.RemoteCommand import RemoteCommand
from Base.Support.FS import FS
from Base.Support.Target import Target

# ----------------------------------------------------------------------
# * shine tune
# ----------------------------------------------------------------------
class Tune(RemoteCommand):

    def __init__(self):
        RemoteCommand.__init__(self)

        self.fs_support = FS(self)

    def get_name(self):
        return "tune"

    def get_desc(self):
        return "Tune file system servers."

    def execute(self):
        
        for fsname in self.fs_support.iter_fsname():
            
            conf = Configuration(fs_name=fsname)
            
            if self.local_flag or self.remote_call:
                fs = FSLocal(conf)
            else:
                fs = FSProxy(conf)
                
            # Is the tuning configuration file name specified ?               
            if Globals().get_tuning_file().strip() == "":
                # No.  Create an empty tuning model.
                tuning = TuningModel()
            else:
                # Yes.
                # Load the tuning configuration file
                tuning = TuningModel(filename=Globals().get_tuning_file())
                try:
                    # Parse the tuning model
                    tuning.parse()
                                    
                    # Add the quota tuning parameters to the tuning model.
                    fs.add_quota_tuning(tuning)
                    
                except TuningParameterDeclarationException, tpde:
                    # An error has occured during parsing of tuning configuration file
                    print "%s" %(str(tpde))
                    # Break the tuning process for the currently processed file system
                    continue
                
            fs.tune(tuning)

    def output(self, dic):
        if self.remote_call:
            self._print_pickle(dic)
        else:
            print "%s" % dic


