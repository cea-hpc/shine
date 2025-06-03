# Config.py -- Display component configuration
# Copyright (C) 2012-2015 CEA
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

from Shine.CLI.Display import display

from Shine.Commands.Base.FSLiveCommand import FSLiveCommand

#
# NOTE: This command is declared as a FSLiveCommand but it does not do any live
# actions!
# This is for convenience only as FSLiveCommand has already most of what this
# needs to run.
#
class Config(FSLiveCommand):
    """
    shine config -f foo -O "%fsname"
    """

    NAME = "config"
    DESCRIPTION = "Display filesystem component information"

    def execute_fs(self, fs, fs_conf, hdl, vlevel):
        print(display(self, fs))
        return 0
