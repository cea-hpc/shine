# Storage.py -- File storage config backend (storage.conf)
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

from Shine.Configuration.ModelFile import ModelFile, SubElement
from Shine.Configuration.Globals import Globals
from Shine.Configuration.TargetDevice import TargetDevice

class Storage(ModelFile):

    syntax = { 
        'mgt' :     'subelem',
        'mdt' :     'subelem',
        'ost' :     'subelem'
    }

    def __init__(self, file):
        ModelFile.__init__(self, file)

    def sub_element(self, key, value):
        return FileDevice(key, value)

    def get_target_devices(self, target):
        devices = ModelFile.get_with_dict(self, target)
        target_devices = []
        for dict in devices:
            target_devices.append(TargetDevice(target, dict))
        return target_devices


class FileDevice(SubElement):
    syntax = {
        'name'      : 'string',
        'node_name' : 'string',
        'dev'       : 'path',
        'size'      : 'digit',
        'jdev'      : 'path',
        'jsize'     : 'digit',
    }
