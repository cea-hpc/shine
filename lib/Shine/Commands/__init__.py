# Commands/__init__.py -- Commands module initialization
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


# ----------------------------------------------------------------------
# List of enabled commands classes.
# ----------------------------------------------------------------------

commandList = []

#for cmd in [ "ShowConf",
#             "Show",
#             "Install",
#             "Edit",
#             "Format",
#             "List",
#             "Start",
#             "Stop",
#             "Info",
#             "Status",
#             "Mount",
#             "Umount",
#             "Test",
#             "Cache",
#             "Remove",
#             "Tune"]:
for cmd in [ "Show",
             "Install",
             "Remove",
             "Format",
             "Status",
             "Start",
             "Stop",
             "Fsck",
             "Mount",
             "Umount",
             "Tune"]:
    # Import command class file
    mod = __import__(cmd, globals(), locals(), [cmd])

    # Add class to global command list
    commandList.append(getattr(mod, cmd))

