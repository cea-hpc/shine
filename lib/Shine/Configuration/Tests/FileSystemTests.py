#!/usr/bin/env python
# Shine.Configuration.FileSystem test suite
# Written by S. Thiell 2008-03-21
# $Id$


"""Unit test for FileSystem"""

import copy
import sys
import unittest

sys.path.append('../../..')

from Shine.Configuration.FileSystem import FileSystem


class FileSystemTests(unittest.TestCase):

    def testNidMap1(self):
        f = FileSystem()
        nid_map = f._setup_nid_map("fortoy3 fortoy3-ib@o2ib0")
        #assert nodes.as_ranges() == "cws-cors"
        #assert list(nodes) == [ "cws-cors" ]


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(FileSystemTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
