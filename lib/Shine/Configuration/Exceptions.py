# Exceptions.py -- Configuration exception classes
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

#from Model import ModelDevice

class ConfigException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class ConfigSyntaxError(ConfigException):
    def __init__(self, file, line_nbr, line):
        self.file = file
        self.lineNbr = line_nbr
        self.line = line
        self.message = "Syntax error in %s at line %d: \"%s\"" % \
                       (self.file, self.lineNbr, self.line)

class ConfigDeviceNotFoundError(ConfigException):
    def __init__(self, model_dev):
        self.model_dev = model_dev
        self.message = "No matching device found for \"%s\"" % model_dev

class ConfigBadNidMapError(ConfigException):
    def __init__(self, nodes, nids):
        self.nodes = nodes
        self.nids = nids
        self.message = "Erroneous NID map : %s -> %s" % (self.nodes, self.nids)

