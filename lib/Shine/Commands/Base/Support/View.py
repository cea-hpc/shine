# View.py -- Impl. class for view, the -V <view> option
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

from Shine.Commands.Exceptions import CommandBadParameterError

class View:
    """
    Command support class for "-v <view>" command option.
    """
    
    def __init__(self, cmd, optional=True):

        attr = { 'optional' : optional,
                 'hidden' : False,
                 'doc' : "specify view keyword" }

        self.cmd = cmd
        self.cmd.add_option('V', 'view', attr)
    
    def get_view(self):
        if not self.cmd.opt_V:
            return None

        value = self.cmd.opt_V.lower()
        if value not in [ 'fs', 'target', 'disk' ]:
            raise CommandBadParameterError(value, "fs, target, disk")
        return value
