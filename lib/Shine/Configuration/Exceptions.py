# Exceptions.py -- Configuration exception classes
# Copyright (C) 2007-2010 CEA
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

class ConfigException(Exception):
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    def __str__(self):
        return self.message

class ConfigDeviceNotFoundError(ConfigException):
    """A target, described in a model file, cannot be found."""
    def __init__(self, model_dev):
        msg = "No matching device found for \"%s\"" % model_dev
        ConfigException.__init__(self, msg)
        self.model_dev = model_dev

class ConfigInvalidFileSystem(ConfigException):
    """Error indicating the filesystem configuration is not correct."""
    def __init__(self, fs, message):
        ConfigException.__init__(self, message)
        self._fs = fs
