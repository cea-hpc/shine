# MDT.py -- Lustre MDT
# Copyright (C) 2007 CEA
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
from Shine.Utilities.Cluster.Task import Task
from Shine.Utilities.Cluster.Worker import Worker

from Target import Target

from Actions.Format import Format

import socket

class MDT(Target):

    def __init__(self, cf_target, fs):
        Target.__init__(self, cf_target, fs)
        self.target_name = "MDT"

    def test(self):
        print "test MDT %s" % self

    def start(self):
        self._mount()

    def stop(self):
        self._umount()

    def status(self):
        # Generic target checks
        Target.status(self)

        # Wrong status if the device doesn't exist
        #mode = os.stat(os.path.join("/proc/fs/lustre/mdt", self.label)[stat.ST_MODE]
        #if not stat.S_ISDIR(mode):
        #    raise StatusTargetNotMountedError(self)


