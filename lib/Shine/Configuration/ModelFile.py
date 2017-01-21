# Copyright (C) 2010-2014 CEA
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

"""
ModelFile handles ModelFile configuration file manipulation.

You must declare each supported field and syntax:
    model = ModelFile()
    model.add_element('name', check='string')
    ...

You can create your own types.
    class MyElement(SimpleElement):
        def _validate(self, data):
            if len(data) > 10:
                raise ModelFileValueError("Data too long")

    model.add_custom('title', MyElement())

You can load and save from disk.
    model = ModelFile()
    model.load("/tmp/modelfile")
    model.save("/tmp/modelfile.copy")
"""

import re
import copy
import shlex

from ClusterShell.NodeSet import RangeSet

class ModelFileValueError(Exception):
    """Raise when a bad value is used when adding a data or parsing a file."""

class SimpleElement(object):
    """
    A data storing class for ModelFile.

    It handles the checking and storing of a value based on checking-type.
    It could be inherited to implement custom type for ModelFile.
    """

    def __init__(self, check, default=None, values=None):
        self._content = None
        self._check = check
        self._default = default
        self._values = values or []

    def emptycopy(self):
        """Return a new empty copy of this element, with the same attributes."""
        return type(self)(self._check, self._default, self._values)

    def copy(self):
        """Return a deep copy of an SimpleElement."""
        return copy.deepcopy(self)

    # Readers
    def get(self, default=None):
        """
        Return, by priority, one of those: the element content or the element
        default or the provided default value.
        """
        if self._content is not None:
            return self._content
        elif self._default is not None:
            return self._default
        else:
            return default

    def content(self, default=None):
        """For SimpleElement, behave like get()."""
        return self.get(default)

    def __iter__(self):
        yield self._content

    def __str__(self):
        return str(self._content)

    def __len__(self):
        return int(self._content is not None)

    def key(self):
        """
        Unique identifier used for comparison in MultipleElement list.
        By default this is self.
        """
        return self

    def __hash__(self):
        return hash(self.__class__) ^ hash(self._content) ^ hash(self._check)

    def __eq__(self, other):
        if type(other) != type(self):
            return NotImplemented
        return self._content == other._content and self._check == other._check

    def as_dict(self):
        """Helper method for ModelFile.as_dict().

        Return same content than get().
        """
        return self.get()

    def diff(self, other):
        """
        Compare this SimpleElement with another one and return a tuple with 3
        elements. If the two elements are the same, the tuple contains:
         3 empty copy is this element,
        if they are different, it returns:
         an empty copy, a copy of the other element and an empty copy.
        """
        if self == other:
            return self.emptycopy(), self.emptycopy(), self.emptycopy()
        elif len(self) == 0 and len(other) == 1:
            return other.copy(), self.emptycopy(), self.emptycopy()
        elif len(self) == 1 and len(other) == 0:
            return self.emptycopy(), self.emptycopy(), self.copy()
        else:
            return self.emptycopy(), other.copy(), self.emptycopy()

    # Setters
    def replace(self, data):
        """Replace the content with `data'."""
        self.clear()
        self.add(data)

    def clear(self):
        """Clear the element content."""
        self._content = None

    def _validate(self, value):
        """
        Check that @value is valid regarding to SimpleElement check type.

        This function will convert @value to the type correspoding to the check
        type, and returns it.
        It raises a ModelFileValueError is check type is not respected.
        """
        if self._check == 'digit':
            try:
                if str(value)[0:2] == "0x":
                    retval = int(value, base=16)
                else:
                    retval = int(value)
            except ValueError, error:
                raise ModelFileValueError(str(error))
            return retval

        elif self._check == 'boolean':
            if value.lower() in ['yes', 'true', '1' ]:
                return True
            elif value.lower() in ['no', 'false', '0' ]:
                return False
            else:
                raise ModelFileValueError("'%s' not a boolean value" % value)

        elif self._check == 'string':
            if type(value) is not str:
                raise ModelFileValueError("'%s' not a string" % value)
            return str(value)

        elif self._check == 'enum':
            if str(value) not in [str(val) for val in self._values]:
                msg = "%s not in %s" % (value, self._values)
                raise ModelFileValueError(msg)
            return [val for val in self._values if str(val) == str(value)].pop()

        elif self._check == 'path':
            if not re.match("^\/([\.\w:-]+/)*[\.\w:-]+/?$", value):
                raise ModelFileValueError("'%s' is not a valid path" % value)
            return value

        else:
            raise TypeError("Check type: %s is unmanaged" % self._check)

    def add(self, value):
        """Validate and set the SimpleElement value.

        Raises aModelFileValueError is called twice. See MultipleElement if you need
        multiple values.
        """
        # Simple element could not 'add' several times. See MultipleElement.
        if self._content is not None:
            raise KeyError("Content already set to '%s'" % self._content)

        # Check value has a valid content.
        self._content = self._validate(value)

    def parse(self, data):
        """Parse, validate and set the SimpleElement value.

        See add() for more details.
        """
        self.add(data)

def _changify(newobj, oldobj):
    """
    Store comparison information into `newobj' based on `oldobj'.

    MultipleElement can have different type of elements, based on different
    classes. These classes have no common super class.
    MultipleElement.diff() method returns a list of changed objects. For
    convenience, those objects will be polymorphic and will contain their
    update information and also the old ones.
    """
    setattr(newobj, 'old', oldobj)
    setattr(newobj, 'chgkeys', set())
    # For convenience, pre-compute the list of modified keys
    for data in newobj.old.diff(newobj):
        newobj.chgkeys.update(data)
    # If needed, we can also add some methods dynamically.

    # This function could evolve to a generic class which will be used by
    # SimpleElement, MultipleElement and ModelFile if needed.
    return newobj

class MultipleElement(object):
    """
    This is a container over a list of non-multiple element, like SimpleElement or
    ModelFile.

    It uses the provided instance, at init, as a reference for all the data that
    it will have to manage.
    """

    def __init__(self, orig_elem, enable_ranges=True):
        self._origelem = orig_elem
        self._elements = []
        self._enable_ranges = enable_ranges

    def emptycopy(self):
        """Return a new empty copy of this element, with the same attributes."""
        return type(self)(self._origelem.emptycopy())

    def copy(self):
        """Return a deep copy of a MultipleElement."""
        return copy.deepcopy(self)

    # Readers
    def elements(self):
        """Access to defined element objects and contents."""
        return self._elements

    def get(self, default=None):
        """Return a list containing all element data.

        See SimpleElement.get().
        """
        return list(self) or default

    def key(self):
        """
        Unique identifier used for comparison in MultipleElement list.
        By default this is self.
        """
        return self

    def content(self, default=None):
        """For MultipleElement, it behaves like get()."""
        return self.get(default)

    def __getitem__(self, idx):
        return self.get()[idx]

    def __iter__(self):
        return (elem.content() for elem in self.elements())

    def __len__(self):
        return len(self.elements())

    def __str__(self):
        return " ".join([str(elem) for elem in self])

    def __eq__(self, other):
        return self._origelem == other._origelem \
                and self.elements() == other.elements()

    def __hash__(self):
        value = hash(self.__class__) ^ hash(self._origelem)
        for elem in self._elements:
            value = value ^ hash(elem)
        return value

    def as_dict(self):
        """Helper method for ModelFile.as_dict().

        Return a list with all contained element transformed with as_dict().
        """
        return [elem.as_dict() for elem in self.elements()]

    def diff(self, other):
        """Compare a MultipleElement with another one.

        Return a tuple of three new MultipleElements.
        First one contains only the elements added in other.
        Second one contains the modified elements, from other.
        Third one contains only the elements removed from self.
        """
        localdict = dict((elem.key(), elem) for elem in self.elements())
        otherdict = dict((elem.key(), elem) for elem in other.elements())

        # Detect new elements in other. Add them keeping order.
        added = self.emptycopy()
        for elem in other.elements():
            if elem.key() not in localdict:
                added.elements().append(elem.copy())

        # Detect missing elements in other. Add them keeping order.
        removed = self.emptycopy()
        for elem in self.elements():
            if elem.key() not in otherdict:
                removed.elements().append(elem.copy())

        # Detect modified element in other.
        # Add the new one from other
        changed = self.emptycopy()
        for elem in self.elements():
            key = elem.key()
            if key in otherdict:
                otherelem = otherdict[key]
                e_added, e_changed, e_removed = elem.diff(otherelem)
                if e_added or e_changed or e_removed:
                    newelem = _changify(otherelem.copy(), elem.copy())
                    changed.elements().append(newelem)

        return added, changed, removed

    # Setters
    @classmethod
    def _expand_range(cls, data):
        """
        Return an iterator on multiple lines based on the ranges the provided
        data contains.
        """

        fmt = ''       # Format string
        rng_list = []  # List of ranges found
        while data.find('[') >= 0:
            pfx, sfx = data.split('[', 1)
            rng, data = sfx.split(']', 1)
            rng_list.append(rng)
            fmt += "%s%%s" % pfx
        fmt += data

        # If no range is found, no more work is needed
        if not rng_list:
            return iter([data])

        # Create range iterators for all ranges found.
        rangesets = [RangeSet(rng) for rng in rng_list]

        # Verify that all ranges have the same length
        minsize = min([len(rng) for rng in rangesets])
        maxsize = max([len(rng) for rng in rangesets])
        if minsize != maxsize:
            raise ModelFileValueError("Range size mismatch %d != %d" %
                             (minsize, maxsize))

        # Need striter() to build padded strings if present
        rangesets = [list(rng.striter()) for rng in rangesets]

        # Generate the new lines based from the rangeset
        return (fmt % tpl for tpl in zip(*rangesets))

    def add(self, value):
        """Add a new element to this MultipleElement and call add() on it."""
        newone = self._origelem.emptycopy()
        newone.add(value)
        self._elements.append(newone)

    def parse(self, data):
        """Add a new element to this MultipleElement and call parse() on it."""
        if self._enable_ranges:
            lines = self._expand_range(data)
        else:
            lines = [data]

        for data in lines:
            newone = self._origelem.emptycopy()
            newone.parse(data)
            self._elements.append(newone)

    def replace(self, value):
        """Replace current content with `value'."""
        self.clear()
        self.add(value)

    def __delitem__(self, idx):
        del self._elements[idx]

    def remove(self, value):
        """Remove element containing value."""
        elem = self._origelem.emptycopy()
        elem.add(value)
        if elem not in self.elements():
            raise KeyError("%s not in MultipleElement" % value)
        self.elements().remove(elem)

    def clear(self):
        """Remove all elements from this MultipleElement."""
        self._elements = []



class ModelFile(object):
    """
    Manipulate a ModelFile in memory.

    A ModelFile has defined elements. It tell what value are supported.
    Each elements could a SimpleElement, a MultipleElement or a custom one.

    You can handle a ModelFile more or less like a dict. It could be save to
    disk and load from it.
    """

    def __init__(self, sep=':', linesep="\n"):
        self._sep = sep
        self._linesep = linesep
        self._elements = {}

    def emptycopy(self):
        """Return a new empty copy of this element, with the same attributes."""
        newone = type(self)(self._sep, self._linesep)
        # Some elements could be defined in __init__, or added manually.
        # Add what's missing
        missing = set(self.elements()) - set(newone.elements())
        for name in missing:
            newone.add_custom(name, self.elements()[name].emptycopy())
        return newone

    def copy(self):
        """Return a deep copy of ModelFile."""
        return copy.deepcopy(self)

    # Element management

    def elements(self, key=None):
        """Access to defined element objects and contents."""
        if key is not None:
            return self._elements.get(key)
        return self._elements

    def add_element(self, name, multiple=False, **kwargs):
        """Add a new supported SimpleElement with key `name`.

        - multiple: If several values could be associated to this key.
        - check: type of element in
                        ['string', 'digit', 'enum', 'path', 'boolean']
        - values: accepted values for 'enum' check.

        See `SimpleElement`.
        """
        self.add_custom(name, SimpleElement(**kwargs), multiple)

    def add_custom(self, name, custom_elem, multiple=False, expand_range=True):
        """Add a custom Element type.

        This could be any element that supports needed interface.
        See `SimpleElement` or `MultipleElement`for examples."""
        if name in self._elements:
            raise KeyError("%s is already declared" % name)

        if multiple:
            self._elements[name] = MultipleElement(custom_elem, expand_range)
        else:
            self._elements[name] = custom_elem

    def del_element(self, name):
        """
        Deletes a element definition and its content, which was added using
        add_element() or add_custom().
        """
        del self._elements[name]

    def is_element(self, name):
        """Test if `name` is declared. It could be empty."""
        return name in self._elements

    def key(self):
        """
        Unique identifier used for comparison in MultipleElement list.
        By default this is self.
        """
        return self

    # Readers
    def get(self, key, default=None):
        """Return data associated to element pointed by key.

        Optionaly default could be used if current value is None.
        """
        return self._elements[key].content(default)

    def content(self, default=None):
        """Return an object behaving like a dict.

        Optional default will be returned if this is empty."""
        if self._elements:
            return self
        else:
            return default

    def __str__(self):
        elems = []
        for key, values in self.iteritems():
            strval = str(values)
            # Inlined ModelFile: add quotes to string values containing spaces
            if self._linesep == ' ' and  ' ' in strval:
                strval = '"' + strval + '"'
            elems.append(''.join([key, self._sep, strval]))
        return self._linesep.join(elems)

    def __len__(self):
        return len(list(self.iterkeys()))

    # To behave more like a dict
    def __contains__(self, key):
        """Test if specified key has a non None content."""
        return self.get(key, None) is not None

    def __getitem__(self, key):
        return self.get(key)

    def __delitem__(self, key):
        self._elements[key].clear()

    def iterkeys(self):
        """Iterate over the keys with non-empty value."""
        return (key for key, value in self._elements.iteritems() if len(value))

    def iteritems(self):
        """Iterate over the keys and non-empty values.
        Multiple elements will yield for each element in it."""
        for key, element in self._elements.iteritems():
            if len(element):
                for value in element:
                    yield key, value

    # Content access

    def add(self, key, value):
        """Add a new value for element linked to @key.

        @value is analyzed by the element itself."""
        self._elements[key].add(value)

    def replace(self, key, value):
        """Replace the content of `key' with `data'."""
        self._elements[key].replace(value)

    def __iter__(self):
        return self.iterkeys()

    def __eq__(self, other):
        if type(other) != type(self):
            return NotImplemented
        return self._sep == other._sep and self._linesep == self._linesep \
                and self.elements() == other.elements()

    def __hash__(self):
        value = hash(self.__class__)
        for key, elem in self._elements.iteritems():
            value = value ^ hash(key) ^ hash(elem)
        return value

    def diff(self, other):
        """Compare a ModelFile with another one.

        Return a tuple of three new ModelFiles:
        First one contains only the elements added in other.
        Second one contains an empty MultipleElement.
        Third one contains only the elements removed from self.
        """

        localkeys = set(self.iterkeys())
        otherkeys = set(other.iterkeys())

        added = self.emptycopy()
        for key in otherkeys - localkeys:
            added.elements()[key] = other.elements()[key].copy()

        removed = self.emptycopy()
        for key in localkeys - otherkeys:
            removed.elements()[key] = self.elements()[key].copy()

        changed = self.emptycopy()
        for key in localkeys & otherkeys:
            elemadded, elemchanged, elemremoved = \
                self.elements()[key].diff(other.elements()[key])
            if elemadded:
                added.elements()[key] = elemadded.copy()
            if elemremoved:
                removed.elements()[key] = elemremoved.copy()
            if elemchanged:
                changed.elements()[key] = elemchanged.copy()

        return added, changed, removed


    # Representation

    def as_dict(self):
        """Return a dict containing all elements and content using only Python
        built-in objects."""
        return dict([(key, self._elements[key].as_dict())
            for key in self.iterkeys()])

    def parse(self, data):
        """Parse @data based on separators and declared elements."""
        if self._linesep == ' ':
            # Inlined ModelFile: split using shlex to support quotes
            splitted = shlex.split(data)
        else:
            splitted = data.split(self._linesep)

        for line in splitted:
            if line:
                try:
                    key, value = line.split(self._sep, 1)
                    if self._linesep == ' ':
                        # Unquote inlined ModelFile values
                        value = ' '.join(shlex.split(value))
                except ValueError:
                    raise ModelFileValueError("Wrong syntax '%s'" % line)
                try:
                    self._elements[key.strip()].parse(value.strip())
                except KeyError, exp:
                    raise ModelFileValueError("Unknown key %s" % exp)

    # File handling
    def load(self, filename):
        """Fill a model file using data from file pointed by filename."""
        modelfd = open(filename)
        for nbr, line in enumerate(modelfd):
            # Remove comments and blank lines
            line = line.split('#', 1)[0].strip()
            if line:
                try:
                    self.parse(line)
                except ModelFileValueError, error:
                    raise ModelFileValueError("%s at %s:%d" % \
                                                (error, filename, nbr + 1))
        modelfd.close()

    def save(self, filename, header=None):
        """Write model file content to specified file.

        `header` could be optionaly use to add some specific content as file
        start."""
        modelfd = open(filename, 'w+')
        if header:
            modelfd.write("%s\n" % header)
        modelfd.write("%s\n" % self)
        modelfd.close()
