#!/usr/bin/env python
# Shine.Configuration.TuningModel test suite
# Written by A. Degremont 2010-01-19


"""Unit test for Model"""

import unittest

from Utils import makeTempFile
from ClusterShell.NodeSet import NodeSet
from Shine.Configuration.TuningModel import TuningModel, TuningParameter, TuningError

class TuningModelTest(unittest.TestCase):

    def makeTempTuningModel(self, text):
        """
        Create a temporary file instance and returns a TuningModel with it.
        """
        self.f = makeTempFile(text)
        model = TuningModel(filename=self.f.name)
        return model

    def test_tuning_param_str(self):
        """test TuningParameter.__str__()"""
        param = TuningParameter("foo", 0, ('mds', 'clt'), ["toto15"])
        self.assertEqual(str(param), "foo=0 types=mds,client nodes=toto15")

    def testExampleFile(self):
        """test example tuning"""
        m = TuningModel(filename="../conf/tuning.conf.example")
        m.parse()

    def testEmptyFile(self):
        """test empty tuning"""
        m = self.makeTempTuningModel("")
        m.parse()
        self.assertEqual(len(m._parameter_dict.keys()), 0)

    def testComments(self):
        """test comments and blank lines"""
        m = self.makeTempTuningModel("""
# This is a comment

   #### Another one ##

        """)
        m.parse()
        self.assertEqual(len(m._parameter_dict.keys()), 0)

    def testSimpleFile(self):
        """test simple tuning"""
        m = self.makeTempTuningModel("""
alias panic_on_lbug=/proc/sys/lnet/panic_on_lbug
1 panic_on_lbug MDS;OSS;CLT""")
        m.parse()

        # We have one tuning for each
        tuning = TuningParameter("/proc/sys/lnet/panic_on_lbug", "1", \
                                 ["mds","oss","clt"], None)
        for t in ["oss","mds","client"]:
            tunings = m.get_params_for_name(None, [t])
            self.assertEqual(len(tunings), 1)
            self.assertTrue(tunings[0], tuning)

    def testAliasMissing(self):
        """test tuning with missing alias"""
        m = self.makeTempTuningModel("bar foo CLT")
        self.assertRaises(TuningError, TuningModel.parse, m)

    def testWrongSyntax(self):
        """test tuning with wrong syntax"""
        m = self.makeTempTuningModel("""
alias foo=/foo
bar foo CLT ; MDS""")
        self.assertRaises(TuningError, TuningModel.parse, m)

    def testFileValue(self):
        """test tuning with path as value"""
        m = self.makeTempTuningModel("""
alias daemon_file = /proc/sys/lnet/daemon_file
/tmp/toto.log daemon_file MDS;OSS;CLT""")
        m.parse()

        # We have one tuning for each
        tuning = TuningParameter("/proc/sys/lnet/daemon_file", \
                                 "/tmp/toto.log", \
                                 ["mds","oss","clt"], None)
        for t in ["oss","mds","client"]:
            tunings = m.get_params_for_name(None, [t])
            self.assertEqual(len(tunings), 1)
            self.assertTrue(tunings[0], tuning)

    def testQuotedValue(self):
        """test tuning with a quoted value"""
        m = self.makeTempTuningModel("""
alias daemon_file=/proc/sys/lnet/daemon_file
"/tmp/toto space.log" daemon_file MDS;OSS;CLT""")
        m.parse()

        # We have one tuning for each
        tuning = TuningParameter("/proc/sys/lnet/daemon_file", \
                                 '"/tmp/toto space.log"', \
                                 ["mds","oss","clt"], None)
        for t in ["oss","mds","client"]:
            tunings = m.get_params_for_name(None, [t])
            self.assertEqual(len(tunings), 1)
            self.assertTrue(tunings[0] == tuning)

    def testOnNodes(self):
        """test tuning with nodes"""
        m = self.makeTempTuningModel("""
alias panic_on_lbug=/proc/sys/lnet/panic_on_lbug
1 panic_on_lbug MDS;CLT;foo[1-5]""")
        m.parse()

        # We have one tuning for each
        tuning = TuningParameter("/proc/sys/lnet/panic_on_lbug", "1", \
                                 ["mds","clt"], NodeSet("foo[1-5]"))
        # Check node types
        for t in ["mds","client"]:
            tunings = m.get_params_for_name(None, [t])
            self.assertEqual(len(tunings), 1)
            self.assertTrue(tunings[0] == tuning)
        # Check node name
        tunings = m.get_params_for_name(NodeSet("foo[1-2]"), [])
        self.assertEqual(len(tunings), 1)
        self.assertTrue(tunings[0] == tuning)

    def test_router_is_supported(self):
        """test ROUTER is a supported node type"""
        model = self.makeTempTuningModel("""
alias panic_on_lbug=/proc/sys/lnet/panic_on_lbug
1 panic_on_lbug ROUTER""")
        model.parse()
        tuning = TuningParameter("/proc/sys/lnet/panic_on_lbug", "1",
                                 ['router'])
        tunings = model.get_params_for_name(None, ['router'])
        self.assertEqual(len(tunings), 1)
        self.assertEqual(tunings[0], tuning)

    def test_double_param_declaration(self):
        """test that a parameter declared twice raises an error"""
        model = self.makeTempTuningModel("""
alias panic_on_lbug=/proc/sys/lnet/panic_on_lbug
1 panic_on_lbug ROUTER
0 panic_on_lbug ROUTER""")
        self.assertRaises(TuningError, model.parse)
