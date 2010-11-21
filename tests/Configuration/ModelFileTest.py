#!/usr/bin/env python
# Shine.Configuration.ModelFile test suite
# Written by A. Degremont 2010-10-12
# $Id$


"""Unit test for ModelFile"""

import os
import unittest

from Utils import makeTempFile, makeTempFilename
from ClusterShell.NodeSet import NodeSet
from Shine.Configuration.ModelFile import ModelFile, SimpleElement, \
                                          MultipleElement


class SimpleElementTest(unittest.TestCase):

    def element_tests(self, elem, toadd, toread, diffadd, diffread=None):
        """base function to build a test for SimpleElement"""
        self.assertEqual(elem.get(), None)
        self.assertEqual(len(elem), 0)

        if diffread is None:
            diffread = diffadd

        # Default value for get()
        self.assertEqual(elem.get('def'), 'def')

        # SimpleElement as a content and test get()
        elem.add(toadd)
        self.assertEqual(elem.get(), toread)
        self.assertEqual(elem.get('def'), toread)
        self.assertEqual(len(elem), 1)

        # Convert to string
        self.assertEqual(str(elem), str(toread))

        # replace()
        elem.replace(diffadd)
        self.assertEqual(elem.get(), diffread)

        # clear()
        elem.clear()
        self.assertEqual(elem.get(), None)

        # parse()
        elem.parse(str(toadd))
        self.assertEqual(elem.get(), toread)

        # as_dict()
        self.assertEqual(elem.as_dict(), toread)

        # diff()
        # ==
        added, changed, removed = elem.diff(elem)
        self.assertTrue(len(changed) == len(added) == len(removed) == 0)
        # elem <> (empty)
        added, changed, removed = elem.diff(elem.emptycopy())
        self.assertEqual(removed.get(), toread)
        self.assertTrue(len(added) == len(changed) == 0)
        # (empty) <> elem
        added, changed, removed = elem.emptycopy().diff(elem)
        self.assertEqual(added.get(), toread)
        self.assertTrue(len(changed) == len(removed) == 0)
        # elem <> other
        other = elem.emptycopy()
        other.add(diffadd)
        added, changed, removed = elem.diff(other)
        self.assertEqual(changed.get(), diffread)
        self.assertTrue(len(added) == len(removed) == 0)

    def testGenericTestSimpleElement(self):
        """test common SimpleElement methods"""
        elem = SimpleElement('string', default='foo')
        self.assertEqual(elem.get(), 'foo')

        # Could not add twice
        elem.add('foo')
        self.assertRaises(ValueError, elem.add, 'bar')

        elem.clear()
        elem.add('foo')

    def testStringSimpleElement(self):
        """test SimpleElement(check='string')"""
        elem = SimpleElement('string')
        self.element_tests(elem, 'ok', 'ok', 'ko')
        self.assertRaises(ValueError, elem.add, 45)

    def testBooleanSimpleElement(self):
        """test SimpleElement(check='boolean')"""
        elem = SimpleElement('boolean')
        self.element_tests(elem, 'no', False, 'yes', True)

        elem = SimpleElement('boolean')
        self.element_tests(elem, 'True', True, 'False', False)

        elem = SimpleElement('boolean')
        self.element_tests(elem, '0', False, '1', True)

        self.assertRaises(ValueError, elem.add, 'wrong')

    def testDigitSimpleElement(self):
        """test SimpleElement(check='digit')"""
        elem = SimpleElement('digit')
        self.element_tests(elem, 45, 45, 54)
        self.assertRaises(ValueError, elem.add, 'notadigit')

    def testEnumSimpleElement(self):
        """test SimpleElement(check='enum')"""
        elem = SimpleElement('enum', values=[.25, .50, .75])
        self.element_tests(elem, .25, .25, .50)
        self.assertRaises(ValueError, elem.add, 'notinlist')

    def testPathSimpleElement(self):
        """test SimpleElement(check='path')"""
        elem = SimpleElement('path')
        self.element_tests(elem, '/mnt/lustre', '/mnt/lustre', '/mnt/foo')
        self.assertRaises(ValueError, elem.add, 'not a path')

    def testWrongSimpleElement(self):
        """test SimpleElement with a wrong check"""
        elem = SimpleElement('wrong')
        self.assertRaises(TypeError, elem.add, 1)

class MultipleElementTest(unittest.TestCase):

    def testBase(self):
        """MultipleElement base methods"""

        elem = MultipleElement(SimpleElement(check='string'))

        # Default
        self.assertEqual(elem.get([]), [])

        # First add()
        elem.add("3")
        self.assertEqual(elem.get(), ["3"])
        self.assertEqual(elem.content(), ["3"])
        self.assertEqual(elem[0], "3")
        self.assertEqual(str(elem), "3")
        self.assertEqual(len(elem), 1)
        # Second add()
        elem.add("5")
        elem.add("7")
        self.assertEqual(elem.get(), ["3", "5", "7"])
        self.assertEqual(elem.content(), ["3", "5", "7"])
        self.assertEqual(elem[1], "5")
        self.assertEqual(str(elem), "3 5 7")
        self.assertEqual(len(elem), 3)

        # Remove an item
        del elem[1]
        self.assertEqual(elem.get(), ["3", "7"])
        self.assertEqual(len(elem), 2)
        elem.remove("3")
        self.assertEqual(elem.get(), ["7"])
        self.assertEqual(len(elem), 1)
        self.assertRaises(ValueError, elem.remove, "6")

        # replace()
        elem.replace("12")
        self.assertEqual(elem.get(), ["12"])

        # clear()
        elem.clear()
        self.assertEqual(len(elem), 0)

        # parse()
        elem.parse("4")
        self.assertEqual(elem.get(), ["4"])
        self.assertEqual(str(elem), "4")
        self.assertEqual(len(elem), 1)

        # __eq__
        other = elem.emptycopy()
        self.assertNotEqual(elem, other)
        other.add("4")
        self.assertEqual(elem, other)

    def testCopy(self):
        """MultipleElement copy methods"""
        elem = MultipleElement(SimpleElement(check='digit'))

        # Empty
        self.assertEqual(len(elem.emptycopy()), 0)
        self.assertEqual(elem.copy().as_dict(), elem.as_dict())

        # With some content
        elem.add(3)
        elem.add(5)
        self.assertEqual(len(elem.emptycopy()), 0)
        self.assertEqual(elem.copy().as_dict(), elem.as_dict())

    def testDiff(self):
        """MultipleElement diff method"""

        elem = MultipleElement(SimpleElement(check='digit'))

        # (empty) <=> (empty)
        added, changed, removed = elem.diff(elem)
        self.assertTrue(len(added) == len(removed) == len(changed) == 0)

        elem.add(3)
        elem.add(4)

        # itself
        added, changed, removed = elem.diff(elem)
        self.assertTrue(len(added) == len(removed) == len(changed) == 0)

        # elem <=> (empty)
        added, changed, removed = elem.diff(elem.emptycopy())
        self.assertTrue(len(added) == len(changed) == 0)
        self.assertEqual(removed.get(), [3, 4])

        # (empty) <=> elem
        added, changed, removed = elem.emptycopy().diff(elem)
        self.assertTrue(len(removed) == len(changed) == 0)
        self.assertEqual(added.get(), [3, 4])

        # Mixed
        other = elem.copy()
        other.remove(4)
        other.add(5)
        added, changed, removed = elem.diff(other)
        self.assertTrue(len(changed) == 0)
        self.assertEqual(added.get(), [5])
        self.assertEqual(removed.get(), [4])


class ModelFileTest(unittest.TestCase):

    def testNoDeclarationError(self):
        """use of a non-declared element raises an error"""
        model = ModelFile()
        self.assertRaises(KeyError, model.get, 'foo')

    def testModelElementManagement(self):
        """add/del elements to a model file"""
        model = ModelFile()

        # Add an element
        model.add_element('foo', check='path')

        # Add another element with the same key raises an error
        self.assertRaises(KeyError, model.add_element, 'foo', check='string')

        # is_element() accessors
        self.assertTrue(model.is_element('foo'))

        # Undeclared an element
        model.del_element('foo')
        self.assertRaises(KeyError, model.del_element, 'foo')

        # Re-add an element
        model.add_element('foo', check='digit')

    def testModelBaseMethods(self):
        """test ModelFile base methods"""

        model = ModelFile()

        # content() with a default value
        self.assertEqual(model.content('default'), 'default')

        model.add_element('foo', check='string', multiple=True)

        # get() with a default value
        self.assertEqual(model.get('foo', 'default'), 'default')

        # Only key with non-empty value are taken in account
        self.assertEqual(len(model), 0)

        # parse() 
        self.assertRaises(ValueError, model.parse, "foo one two")

        # __contains__() False
        self.assertFalse('foo' in model)

        # iter()
        model.add('foo', "5 6")
        model.add('foo', "6 7")
        self.assertEqual(list(iter(model)), ['foo'])

        # __contains__() True
        self.assertTrue('foo' in model)

    def testModelStandardElement(self):
        """ModelFile with simple Element"""
        model = ModelFile()

        # Type string
        model.add_element('name', check='string')
        self.assertEqual(model.get('name', 'mine'), 'mine')
        model.add('name', 'foo')
        self.assertEqual(model.get('name'), 'foo')
        self.assertEqual(str(model), "name:foo")

        # Default value
        model.add_element('bar', check='string', default='barbar')
        self.assertEqual(model.get('bar'), 'barbar')
        self.assertEqual(model.get('bar', 'mine'), 'barbar')
        # Default value are not used for string representation
        self.assertEqual(str(model), "name:foo")

        # Type digit
        model.add_element('stripe_count', check='digit', default=1)
        self.assertEqual(model.get('stripe_count'), 1)
        model.add('stripe_count', 2)
        self.assertEqual(model.get('stripe_count'), 2)
        self.assertEqual(str(model), "name:foo\nstripe_count:2")

    def testMultipleElement(self):
        """ModelFile with MultipleElement"""
        model = ModelFile()
        model.add_element('foos', check='digit', multiple=True)

        # Default
        self.assertEqual(model.get('foos', []), [])

        # Multiple add()
        model.add('foos', 3)
        self.assertEqual(model.get('foos'), [3])
        self.assertEqual(str(model), "foos:3")
        model.add('foos', 5)
        self.assertEqual(model.get('foos'), [3, 5])
        self.assertEqual(str(model), "foos:3\nfoos:5")

    def testAddCustomElement(self):
        """model file uses a user-defined Element"""
        class ElemNodeSet(SimpleElement):
            def __init__(self, check='string', default=None, values=None):
                SimpleElement.__init__(self, 'string', default, values)

            def _validate(self, value):
                try:
                    return NodeSet(value)
                except:
                    raise ValueError

        model = ModelFile()
        model.add_custom('nodes', ElemNodeSet(), multiple=True)
        model.add_custom('nids', ElemNodeSet(), multiple=True)

        model.add('nodes', 'foo[1-5]')
        self.assertEqual(str(model), "nodes:foo[1-5]")
        self.assertEqual([str(item) for item in model.get('nodes')],
                [str(NodeSet('foo[1-5]'))])
        self.assertRaises(ValueError, model.add, 'nodes', 'bad[15')

    def testCompoundElement(self):
        """test a ModelFile with a compound element"""
        class MyCompound(ModelFile):
            def __init__(self, sep='=', linesep=' '):
                ModelFile.__init__(self, sep, linesep)
                self.add_element('dev', check='path')
                self.add_element('index', check='digit')
                self.add_element('jdev', check='path')
                self.add_element('mode', check='enum', default='managed',
                                 values=['managed', 'external'])

        elem = MyCompound()
        elem.parse("dev=/dev/sdb jdev=/dev/sdc index=4")
        self.assertEqual(elem.get('dev'), '/dev/sdb')
        self.assertEqual(elem.get('jdev'), '/dev/sdc')
        self.assertEqual(elem.get('index'), 4)
        self.assertEqual(elem.get('mode'), 'managed')

        model = ModelFile()
        model.add_element('fsname', check='string')
        model.add_custom('mgt', MyCompound(), multiple=True)
        model.add_custom('mdt', MyCompound(), multiple=True)
        model.add_custom('ost', MyCompound(), multiple=True)

        model.parse("ost: dev=/dev/sdb index=4")
        self.assertEqual(len(model.get('ost')), 1)
        self.assertEqual(model.get('ost')[0].get('dev'), '/dev/sdb')
        self.assertEqual(model.get('ost')[0].get('index'), 4)
        model.parse("ost: dev=/dev/sdd index=5")
        self.assertEqual(len(model.get('ost')), 2)
        self.assertEqual(model.get('ost')[1].get('dev'), '/dev/sdd')
        self.assertEqual(model.get('ost')[1].get('index'), 5)

        self.assertEqual(str(model), "ost:index=4 dev=/dev/sdb\n"
                "ost:index=5 dev=/dev/sdd")

    def testDiffSimpleElement(self):
        """diff between 2 modelfiles with a SimpleElement"""
        model = ModelFile()
        model.add_element('name', check='string')

        model2 = model.emptycopy()

        # Empty models have no difference
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Same model have no difference
        model.add('name', 'foo')
        model2.add('name', 'foo')
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # A value changed
        del model2['name']
        model2.add('name', 'bar')
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {'name': 'bar'})

        # A value added
        del model['name']
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {'name': 'bar'})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # A value removed
        added, changed, removed = model2.diff(model)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {'name': 'bar'})
        self.assertEqual(changed.as_dict(), {})

    def testDiffMultipleElement(self):
        """diff between 2 modelfiles with a MultipleElement"""
        model = ModelFile()
        model.add_element('name', check='string', multiple=True)

        model2 = model.emptycopy()

        # Empty models have no difference
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Same model have no difference
        model.add('name', 'foo')
        model2.add('name', 'foo')
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Add a value
        model2.add('name', 'bar')
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {'name': ['bar']})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Remove a value
        del model2['name']
        model.add('name', 'bar')
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {'name': ['foo', 'bar']})
        self.assertEqual(changed.as_dict(), {})

    def testDiffDictElement(self):
        """diff between 2 modelfiles with a subelement"""
        model = ModelFile()

        element = ModelFile(sep="=", linesep=" ")
        element.add_element('size', check='digit')
        element.add_element('count', check='digit')
        model.add_custom('stripe', element)

        model2 = model.emptycopy()

        # Empty models have no difference
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Same model have no difference
        model.parse('stripe: count=1 size=1000000')
        model2.parse('stripe: count=1 size=1000000')
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Remove an attribute
        del model2.get('stripe')['count']
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {'stripe': {'count': 1}})
        self.assertEqual(changed.as_dict(), {})

        # Change an attribute
        model2.get('stripe').add('count', 2)
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {'stripe': {'count': 2}})

    def testDiffDictMultipleElement(self):
        """diff between 2 modelfiles with a multiple subelement"""
        model = ModelFile()

        element = ModelFile(sep="=", linesep=" ")
        element.add_element('dev', check='string')
        element.add_element('index', check='digit')
        model.add_custom('target', element, multiple=True)

        model2 = model.emptycopy()

        # Empty models have no difference
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Same model have no difference
        model.parse('target: dev=/dev/sda index=1')
        model2.parse('target: dev=/dev/sda index=1')
        self.assertEqual(len(model['target']), 1)
        self.assertEqual(len(model2['target']), 1)
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(), {})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Add a new element
        model2.parse('target: dev=/dev/sdb index=2')
        self.assertEqual(len(model['target']), 1)
        self.assertEqual(len(model2['target']), 2)
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(),
                {'target': [{'index': 2, 'dev': '/dev/sdb'}]})
        self.assertEqual(removed.as_dict(), {})
        self.assertEqual(changed.as_dict(), {})

        # Change an element
        del model2['target']
        model2.parse('target: dev=/dev/sdb index=1')
        added, changed, removed = model.diff(model2)
        self.assertEqual(added.as_dict(),
                {'target': [{'index': 1, 'dev': '/dev/sdb'}]})
        self.assertEqual(removed.as_dict(),
                {'target': [{'index': 1, 'dev': '/dev/sda'}]})
        self.assertEqual(changed.as_dict(), {})

    # File management tests

    def testExpandRange(self):
        """parse ranged line expand correctly"""
        model = ModelFile()
        model.add_element("foo", check="string", multiple=True)

        model.parse("foo: mine[10-15]")
        self.assertEqual(len(model.get('foo')), 6)
        del model['foo']

        model.parse("foo: mine[10-15] second[1-6]")
        self.assertEqual(len(model.get('foo')), 6)
        del model['foo']

        # Ranges mismatch
        self.assertRaises(ValueError, model.parse, "foo: five[1-5] two[1-2]")

    def testLoadModelFromFile(self):
        """load a ModelFile from file"""
        model = ModelFile()
        model.add_element("foo", check="string", multiple=True)
        model.add_element("bar", check="digit", multiple=True)

        testfile = makeTempFile("""foo: my test
bar: 3
foo: another
bar: 1
bar: 2""")
        model.load(testfile.name)
        self.assertEqual(model.get('foo'), ['my test', 'another'])
        self.assertEqual(model.get('bar'), [3, 1, 2])

        # Bad file syntax
        testfile = makeTempFile("""foo bad file""")
        self.assertRaises(ValueError, model.load, testfile.name)

    def testSaveModelToFile(self):
        """save a ModelFile to a file"""

        testfile = makeTempFile("""foo: my test
bar: 3
foo: another
bar: 1
bar: 2""")

        # Create a model
        model = ModelFile()
        model.add_element("foo", check="string", multiple=True)
        model.add_element("bar", check="digit", multiple=True)

        # Load a test file
        model.load(testfile.name)

        # Save it to a new file
        filename = makeTempFilename()
        model.save(filename, "# Some header")

        # Reload the file in another model
        model2 = model.emptycopy()
        model2.load(filename)

        os.unlink(filename)

        # Compare the two files. They should have no difference
        added, changed, removed = model.diff(model2)
        self.assertTrue(len(changed) == len(added) == len(removed) == 0)

if __name__ == '__main__':
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = None

    alltests = unittest.TestSuite()
    alltests.addTest(loader.loadTestsFromTestCase(SimpleElementTest))
    alltests.addTest(loader.loadTestsFromTestCase(MultipleElementTest))
    alltests.addTest(loader.loadTestsFromTestCase(ModelFileTest))

    unittest.TextTestRunner(verbosity=2).run(alltests)
