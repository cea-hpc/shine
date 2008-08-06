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
from Shine.Configuration.ModelFile import ModelFileSyntaxErrorReason
from Shine.Configuration.Globals import Globals
from Shine.Configuration.TargetDevice import TargetDevice


class _RangeIterator:
    """
    Our storage range iterator: deal with extended ranges like:
        4
        2-45
        2-22/2
    or any comma separated list of them:
        0-22/2,40,43,50-59
    """

    def __init__(self, rangestring):
        self.pat = rangestring

    def _get_subranges(self):
        result = []
        if self.pat:
            # Comma separated ranges
            if self.pat.find(',') < 0:
                subranges = [self.pat]
            else:
                subranges = self.pat.split(',')

            for subrange in subranges:
                if subrange.find('/') < 0:
                    step = 1
                else:
                    subrange, step = subrange.split('/', 1)

                step = int(step)

                if subrange.find('-') < 0:
                    if step != 1:
                        raise ModelFileSyntaxErrorReason("Invalid range: %s" % self.pat)
                    begin = end = subrange
                else:
                    begin, end = subrange.split('-', 1)

                # Compute padding and return node range info tuple
                begins = begin.lstrip("0")
                if len(begin) - len(begins) > 0:
                    pad = len(begin)
                else:
                    pad = 0
                begin = int(begin)
                end = int(end)

                result.append((begin, end, step, pad))
            return result

    def __iter__(self):
        """
        Implement a generator.
        """
        for begin, end, step, pad in self._get_subranges():
            for i in range(begin, end + 1, step):
                yield "%0*d" % (pad, i)

    def __len__(self):
        """
        Smart len()
        """
        result = 0
        for begin, end, step, pad in self._get_subranges():
            result += (end - begin)/step + 1
        return result


class Storage(ModelFile):

    syntax = { 
        'mgt' :     'subelem',
        'mdt' :     'subelem',
        'ost' :     'subelem'
    }

    def __init__(self, file):
        ModelFile.__init__(self, file)

    def sub_element(self, key, value):

        # Should we expand device pattern?
        fmt = "" # Format string
        rg_list = [] # List of ranges found
        while value.find('[') >= 0:
            pfx, sfx = value.split('[', 1)
            rg, value = sfx.split(']', 1)
            rg_list.append(rg)
            fmt += "%s%%s" % pfx

        if len(rg_list) == 0:
            # No range, it's a single device entry. Process directly.
            return FileDevice(key, value)

        # Range(s) found, we will return a list of FileDevice.
        result = []

        # Create range iterators for all ranges found.
        rg_iters = [_RangeIterator(rg) for rg in rg_list]

        # Sanity check: all ranges must have the same size
        lastsz = -1
        for it in rg_iters:
            sz = len(it)
            if lastsz > -1 and lastsz != sz:
                raise ModelFileSyntaxErrorReason("Range size mismatch (%d != %d)" % \
                        (lastsz, sz))
            lastsz = sz

        # Generate devices.
        try:
            rg_gens = [it.__iter__() for it in rg_iters]
            while True:
                result.append(FileDevice(key, fmt % tuple([rg_gens[i].next()
                    for i in range(0, len(rg_gens))])))
        except StopIteration:
            pass
        
        return result

    def get_target_devices(self, target):
        devices = ModelFile.get_with_dict(self, target)
        target_devices = []
        for dict in devices:
            target_devices.append(TargetDevice(target, dict))
        return target_devices


class FileDevice(SubElement):
    syntax = {
        'tag'       : 'string',
        'node'      : 'string',
        'ha_node'      : 'string',
        'dev'       : 'path',
        'size'      : 'digit',
        'jdev'      : 'path',
        'jsize'     : 'digit',
    }
