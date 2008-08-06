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

import datetime
import re

class ModelFileException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class ModelFileIOError(ModelFileException):
    def __init__(self, file):
        self.file = file
        self.message = "Cannot access file %s" % file

class ModelFileSyntaxError(ModelFileException):
    def __init__(self, file, line_nbr, line, reason=""):
        self.file = file
        self.lineNbr = line_nbr
        self.line = line
        self.reason = reason
        self.message = "Syntax error in %s at line %d:\n\"%s\"" % \
                       (self.file, self.lineNbr, self.line)
        if len(reason) > 0:
            self.message += "\n%s" % self.reason

class ModelFileSyntaxErrorReason(ModelFileException):
    def __init__(self, reason):
        self.message = reason


class ModelFileKeywordError(ModelFileException):
    def __init__(self, key):
        self.key = key
        self.message = "Invalid keyword '%s'." % (key)

class ModelFileValueError(ModelFileException):
    def __init__(self, key, value, text):
        self.key = key
        self.value = value
        self.message = "Invalid value '%s' for '%s'. %s." % \
                        (value, key, text)



class ModelFile:

    syntax = {}
    defaults = {}

    def __init__(self, filename=None, sep=':'):
        self.keysuplen = 16
        self.valsuplen = 16
        self.set_filename(filename, sep)

    def _parse(self):
        line_nbr = 0
        try:
            file = open(self.filename, 'r')
            for line in file:
                line_nbr += 1
                line = line.split('#', 1)[0].strip()
                if line:
                    key, value = line.split(self.sep, 1)
                    self.add(key.strip(), value.strip())
            file.close()
        except ValueError, e:
            raise ModelFileSyntaxError(self.filename, line_nbr, line)
        except ModelFileSyntaxErrorReason, e:
            raise ModelFileSyntaxError(self.filename, line_nbr, line, e.message)
        except IOError, e:
            raise ModelFileIOError(self.filename)

    def get_filename(self):
        return self.filename

    def set_filename(self, filename, sep=':'):
        self.filename = filename
        self.sep = sep
        self.keys = {}
        if filename:
            self._parse()

    def _add(self, key, value):
        # Key is unknown, create a list with 'value'
        if key not in self.keys:
            self.keys[key] = [value]
            if len(key) > self.keysuplen:
                self.keysuplen = len(key)
        # there's already a list for this key, add the value
        else:
            self.keys[key].append(value)

    def add(self, key, value):

        # Do we have a grammar and params are valid ?
        if self.syntax:
            value = self.validate(key, value)

        # If needed, expand to multiple values (eg. for subelem pattern)
        if type(value) is list:
            for val in value:
                self._add(key, val)
        else:
            self._add(key, value)

    def delete(self, key):
        if self.keys.has_key(key):
            del self.keys[key]

    def get(self, key):
        return self.keys[key]

    def get_one(self, key):
        lst = self.keys.get(key, [''])
        return lst[0]

    def has_key(self, key):
        return self.keys.has_key(key)

    def get_with_dict(self, key):
        lst = [] 
        for e in self.keys[key]:
            if isinstance(e, ModelFile):
                e = e.get_dict()
            lst.append(e)
        return lst

    def get_dict(self):
        result_dict = {}
        for key, val in self.keys.iteritems():
            for e in val:
                if isinstance(e, ModelFile):
                    e = e.get_dict()
                result_dict[key] = e
        return result_dict

    def sub_element(self, key, value, sep = "="):
        return SubElement(self, value, sep)

    def validate(self, key, value):

        # Verify if the keyword exists
        if key not in self.syntax:
            raise ModelFileKeywordError(key)
            
        # If the code is a string, check its meaning
        elif type(self.syntax[key]) is str:
            code = self.syntax[key]
            # The value defined a subelement
            if code == 'subelem':
                return self.sub_element(key, value)
            # The value must be an integer
            elif code == 'digit' and not value.isdigit():
                raise ModelFileValueError(key, value, 'Must be an integer')
            # The value must be a path. FIXME: Can we avoid using a RE here?
            elif code == 'path' and not re.match("^\/([\.\w-]+/)*[\.\w-]+/?$",value):
                raise ModelFileValueError(key, value, 'Must be a path')

            # FIXME: All other cases are valid for the moment...

        # Else, the code must be a list of valid values
        elif value not in self.syntax[key]:
            raise ModelFileValueError(key, value, ' Valid ones are: %s' % \
                                      ",".join(self.syntax[key]))

        # FIXME: All other cases are valid for the moment...
        return value

    def __iter__(self):
        for k, v in self.keys.iteritems():
            for sub_value in v:
                yield k, sub_value

    def __str__(self):
        str = ""
        for k, v in self:
            str += "%s%s %s\n" % (k, self.sep, v)
        return str

    def _keycmp(self, k1, k2):
        return cmp(k1, k2)

    def save(self, path, header):
        f = open(path, 'w+')
        f.write("#" * 72 + "\n")
        f.write("# %s\n" % header)
        f.write("# %s\n" % datetime.datetime.now().ctime())
        f.write("#" * 72 + "\n")
        keylist = self.keys.keys()
        keylist.sort(self._keycmp)
        for k in keylist:
            for sub_value in self.keys[k]:
                f.write("%s: %s\n" % (k, sub_value))
        f.close()

class SubElement(ModelFile):

    def __init__(self, file, line, sep="="):
        self.file = file
        self.sep = sep
        self.line = line
        self.keysuplen = 16
        self.valsuplen = 16
        self.keys = {}
        self._parse()

    def _parse(self):
        try:
            for str in self.line.split():
                key, value = str.split(self.sep, 2)
                self.add(key, value)
        except ValueError:
            if self.file:
                raise ModelFileSyntaxError(self.file.filename, 0, self.line)
            else:
                raise ModelFileException("Internal error.")
            
    def __str__(self):    
        str = ""
        for k,v in self:
            str += "%s%s%s " % (k, self.sep, v)
        return str.strip()

#
# For test purposes only
#
if __name__ == '__main__':
    import sys
    conf = ModelFile(sys.argv[1], sys.argv[2])
    print conf

