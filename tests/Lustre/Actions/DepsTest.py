#!/usr/bin/env python
# Copyright (C) 2013 CEA
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

"""Unit test for Action dependency system."""

import unittest

from ClusterShell.Task import task_self

from Shine.Lustre.Actions.Action import CommonAction, ActionGroup, \
                                        ACT_OK, ACT_WAITING, ACT_ERROR

class TestAction(CommonAction):

    def __init__(self, cmd, timeout=None):
        CommonAction.__init__(self)
        self.launched = False
        self.cmd = cmd
        self.timeout = timeout

    def _launch(self):
        self.task.shell(self.cmd, handler=self, timeout=self.timeout)

    def launch_and_run(self):
        self.launch()
        task_self().run()


class DepsTests(unittest.TestCase):

    def test_group_len(self):
        """Action group length is correct"""
        grp = ActionGroup()
        self.assertEqual(len(grp), 0)
        grp.add(TestAction('/bin/foo'))
        self.assertEqual(len(grp), 1)
        grp.add(TestAction('/bin/bar'))
        self.assertEqual(len(grp), 2)

    def test_simple_ok(self):
        """Action can run a simple command"""
        action = TestAction('/bin/true')
        self.assertEqual(action.status(), ACT_WAITING)

        action.launch_and_run()

        self.assertEqual(action.status(), ACT_OK)

    def test_simple_error(self):
        """Action reports error correctly"""
        action = TestAction('/bin/false')
        self.assertEqual(action.status(), ACT_WAITING)

        action.launch_and_run()

        self.assertEqual(action.status(), ACT_ERROR)

    def test_simple_timeout(self):
        """Action reports timeout as error"""
        action = TestAction('sleep 3', timeout=0.3)
        self.assertEqual(action.status(), ACT_WAITING)

        action.launch_and_run()

        self.assertEqual(action.status(), ACT_ERROR)

    def test_launch_and_run_twice(self):
        """Action could be run twice in a row"""
        class CustomAction(TestAction):
            def __init__(self, cmd):
                TestAction.__init__(self, cmd)
                self._launched = False
            def _launch(self):
                assert(not self._launched)
                TestAction._launch(self)
                self._launched = True

        action = CustomAction('/bin/true')
        self.assertEqual(action.status(), ACT_WAITING)

        # Run once
        action.launch_and_run()
        self.assertEqual(action.status(), ACT_OK)

        # Run twice, it is still fine
        action.launch_and_run()
        self.assertEqual(action.status(), ACT_OK)

    def test_ok_one_dep(self):
        """Dependent actions run fine"""
        act1 = TestAction("/bin/true")
        act2 = TestAction("/bin/true")
        act2.depends_on(act1)

        act1.launch_and_run()
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)

    def test_error_one_dep(self):
        """Action is on error if its dep is on error"""
        act1 = TestAction("/bin/false")
        act2 = TestAction("/bin/true")
        act2.depends_on(act1)

        act1.launch_and_run()
        self.assertEqual(act1.status(), ACT_ERROR)
        self.assertEqual(act2.status(), ACT_ERROR)

    def test_one_dep_relaunch(self):
        """Launch at the bottom of the graph is propagated to top"""
        act1 = TestAction("/bin/true")
        act2 = TestAction("/bin/true")
        act2.depends_on(act1)

        act2.launch_and_run()
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)

    def test_two_deps_ok_launch_bottom(self):
        """Launch at the bottom of the graph is propagated to all deps"""
        act1 = TestAction("/bin/true")
        act2 = TestAction("/bin/true")
        act3 = TestAction("/bin/true")
        act3.depends_on(act1)
        act3.depends_on(act2)

        act3.launch_and_run()
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)
        self.assertEqual(act3.status(), ACT_OK)

    def test_two_deps_ok_launch_top(self):
        """Launch at one head propagates up to the other head"""
        act1 = TestAction("/bin/true")
        act2 = TestAction("/bin/true")
        act3 = TestAction("/bin/true")
        act3.depends_on(act1)
        act3.depends_on(act2)

        act1.launch_and_run()
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)
        self.assertEqual(act3.status(), ACT_OK)

    def test_two_deps_error_launch_top_ok(self):
        """Mix of success and error propagates correctly on deps (ok)"""
        act_ok = TestAction("/bin/true")
        act_error = TestAction("/bin/false")
        act3 = TestAction("/bin/true")
        act3.depends_on(act_ok)
        act3.depends_on(act_error)

        act_ok.launch_and_run()
        self.assertEqual(act_ok.status(), ACT_OK)
        self.assertEqual(act_error.status(), ACT_ERROR)
        self.assertEqual(act3.status(), ACT_ERROR)

    def test_two_deps_error_launch_top_error(self):
        """Mix of success and error propagates correctly on deps (error)"""
        act_ok = TestAction("/bin/true")
        act_error = TestAction("/bin/false")
        act3 = TestAction("/bin/true")
        act3.depends_on(act_ok)
        act3.depends_on(act_error)

        act_error.launch_and_run()
        self.assertEqual(act_ok.status(), ACT_OK)
        self.assertEqual(act_error.status(), ACT_ERROR)
        self.assertEqual(act3.status(), ACT_ERROR)

    def test_two_deps_error_launch_bottom_error(self):
        """Launch at the bottom of the graph with error is handled finely"""
        act_ok = TestAction("/bin/true")
        act_error = TestAction("sleep 0.3; /bin/false")
        act3 = TestAction("/bin/true")
        act3.depends_on(act_ok)
        act3.depends_on(act_error)

        act3.launch_and_run()
        self.assertEqual(act_ok.status(), ACT_OK)
        self.assertEqual(act_error.status(), ACT_ERROR)
        self.assertEqual(act3.status(), ACT_ERROR)

    def test_common_dep_ok_launch_bottom(self):
        """Launch at one sink with a graph with 2 sinks runs fine"""
        act_dep = TestAction("/bin/true")
        act1 = TestAction("/bin/true")
        act2 = TestAction("/bin/true")

        act1.depends_on(act_dep)
        act2.depends_on(act_dep)

        act1.launch_and_run()

        self.assertEqual(act_dep.status(), ACT_OK)
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)

    def test_common_dep_ok_launch_top(self):
        """Launch at the top with a graph with 2 sinks is ok"""
        act_dep = TestAction("/bin/true")
        act1 = TestAction("/bin/true")
        act2 = TestAction("/bin/true")

        act1.depends_on(act_dep)
        act2.depends_on(act_dep)

        act_dep.launch_and_run()

        self.assertEqual(act_dep.status(), ACT_OK)
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)

    def test_common_dep_error_launch_top(self):
        """Launch at the top with a graph with 2 sinks and error"""
        act_dep = TestAction("/bin/false")
        act1 = TestAction("/bin/true")
        act2 = TestAction("/bin/true")

        act1.depends_on(act_dep)
        act2.depends_on(act_dep)

        act_dep.launch_and_run()

        self.assertEqual(act_dep.status(), ACT_ERROR)
        self.assertEqual(act1.status(), ACT_ERROR)
        self.assertEqual(act2.status(), ACT_ERROR)


class ActionGroupTests(unittest.TestCase):

    def setUp(self):
        self.grp = ActionGroup()

    def test_empty(self):
        """Launching an empty group is ok"""
        self.grp.launch()
        task_self().run()
        self.assertEqual(self.grp.status(), ACT_OK)

    def test_one_action(self):
        """A group with its only action both run ok"""
        act = TestAction('/bin/true')
        self.grp.add(act)
        self.grp.launch()
        task_self().run()
        self.assertEqual(act.status(), ACT_OK)
        self.assertEqual(self.grp.status(), ACT_OK)

    def test_two_actions_ok_and_ok(self):
        """A group with 2 actions all run fine"""
        act1 = TestAction('/bin/true')
        act2 = TestAction('/bin/true')
        self.grp.add(act1)
        self.grp.add(act2)
        self.grp.launch()
        task_self().run()
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)
        self.assertEqual(self.grp.status(), ACT_OK)

    def test_one_action_error(self):
        """A group with only an error action is on error"""
        act = TestAction('/bin/false')
        self.grp.add(act)
        self.grp.launch()
        task_self().run()
        self.assertEqual(act.status(), ACT_ERROR)
        self.assertEqual(self.grp.status(), ACT_ERROR)

    def test_two_actions_ok_and_error(self):
        """A group with a ok action and an error action is on error"""
        act1 = TestAction('/bin/true')
        act2 = TestAction('/bin/false')
        self.grp.add(act1)
        self.grp.add(act2)
        self.grp.launch()
        task_self().run()
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_ERROR)
        self.assertEqual(self.grp.status(), ACT_ERROR)

    def test_two_actions_2_errors(self):
        """A group with 2 error actions is on error"""
        act1 = TestAction('/bin/false')
        act2 = TestAction('/bin/false')
        self.grp.add(act1)
        self.grp.add(act2)
        self.grp.launch()
        task_self().run()
        self.assertEqual(act1.status(), ACT_ERROR)
        self.assertEqual(act2.status(), ACT_ERROR)
        self.assertEqual(self.grp.status(), ACT_ERROR)

    def test_one_dep_ok(self):
        """A group with one ok dependency is ok"""
        act = TestAction('/bin/true')
        act1 = TestAction('/bin/true')
        self.grp.add(act1)

        self.grp.depends_on(act)

        self.grp.launch()
        task_self().run()

        self.assertEqual(act.status(), ACT_OK)
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(self.grp.status(), ACT_OK)

    def test_one_dep_error(self):
        """A group with an error dependency is on error, content is not run"""
        act = TestAction('/bin/false')
        act1 = TestAction('/bin/true')
        self.grp.add(act1)

        self.grp.depends_on(act)

        self.grp.launch()
        task_self().run()

        self.assertEqual(act.status(), ACT_ERROR)
        self.assertEqual(act1.status(), ACT_WAITING)
        self.assertEqual(self.grp.status(), ACT_ERROR)

    def test_two_deps_ok_and_ok(self):
        """A group with two ok dependencies is ok"""
        dep1 = TestAction('/bin/true')
        dep2 = TestAction('/bin/true')
        act1 = TestAction('/bin/true')
        self.grp.add(act1)

        self.grp.depends_on(dep1)
        self.grp.depends_on(dep2)

        self.grp.launch()
        task_self().run()

        self.assertEqual(dep1.status(), ACT_OK)
        self.assertEqual(dep2.status(), ACT_OK)
        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(self.grp.status(), ACT_OK)

    def test_two_deps_ok_and_error(self):
        """A group with one error dep and one ok dep is on error"""
        dep1 = TestAction('/bin/true')
        dep2 = TestAction('/bin/false')
        act1 = TestAction('/bin/true')
        self.grp.add(act1)

        self.grp.depends_on(dep1)
        self.grp.depends_on(dep2)

        self.grp.launch()
        task_self().run()

        self.assertEqual(dep1.status(), ACT_OK)
        self.assertEqual(dep2.status(), ACT_ERROR)
        self.assertEqual(act1.status(), ACT_WAITING)
        self.assertEqual(self.grp.status(), ACT_ERROR)

    def test_two_deps_error_and_error(self):
        """A group with 2 error dependencies is on error"""
        dep1 = TestAction('/bin/false')
        dep2 = TestAction('/bin/false')
        act1 = TestAction('/bin/true')
        self.grp.add(act1)

        self.grp.depends_on(dep1)
        self.grp.depends_on(dep2)

        self.grp.launch()
        task_self().run()

        self.assertEqual(dep1.status(), ACT_ERROR)
        self.assertEqual(dep2.status(), ACT_ERROR)
        self.assertEqual(act1.status(), ACT_WAITING)
        self.assertEqual(self.grp.status(), ACT_ERROR)

    def test_one_dep_after_ok(self):
        """An action with an ok group dependency is ok"""
        act = TestAction('/bin/true')
        self.grp = ActionGroup()
        act1 = TestAction('/bin/true')
        self.grp.add(act1)

        act.depends_on(self.grp)

        act.launch()
        task_self().run()

        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(self.grp.status(), ACT_OK)
        self.assertEqual(act.status(), ACT_OK)

    def test_one_dep_after_error(self):
        """An action with an error group dependency is on error"""
        act = TestAction('/bin/true')
        self.grp = ActionGroup()
        act1 = TestAction('/bin/false')
        self.grp.add(act1)

        act.depends_on(self.grp)

        act.launch()
        task_self().run()

        self.assertEqual(act1.status(), ACT_ERROR)
        self.assertEqual(self.grp.status(), ACT_ERROR)
        self.assertEqual(act.status(), ACT_ERROR)

    def test_two_deps_after_ok(self):
        """2 ok actions with an ok group dependency are ok"""
        dep1 = TestAction('/bin/true')
        dep2 = TestAction('/bin/true')
        self.grp = ActionGroup()
        act1 = TestAction('/bin/true')
        self.grp.add(act1)

        dep1.depends_on(self.grp)
        dep2.depends_on(self.grp)

        dep1.launch()
        task_self().run()

        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(self.grp.status(), ACT_OK)
        self.assertEqual(dep1.status(), ACT_OK)
        self.assertEqual(dep2.status(), ACT_OK)

    def test_two_deps_after_error(self):
        """2 ok actions with an error group dependency are on error"""
        dep1 = TestAction('/bin/true')
        dep2 = TestAction('/bin/true')
        self.grp = ActionGroup()
        act1 = TestAction('/bin/false')
        self.grp.add(act1)

        dep1.depends_on(self.grp)
        dep2.depends_on(self.grp)

        dep1.launch()
        task_self().run()

        self.assertEqual(act1.status(), ACT_ERROR)
        self.assertEqual(self.grp.status(), ACT_ERROR)
        self.assertEqual(dep1.status(), ACT_ERROR)
        self.assertEqual(dep2.status(), ACT_ERROR)

    def test_group_dep_ok(self):
        """A ok group which depends on an ok group is ok"""
        grp1 = ActionGroup()
        act1 = TestAction('/bin/true')
        grp1.add(act1)
        grp2 = ActionGroup()
        act2 = TestAction('/bin/true')
        grp2.add(act2)

        grp1.depends_on(grp2)

        grp1.launch()
        task_self().run()

        self.assertEqual(act1.status(), ACT_OK)
        self.assertEqual(grp1.status(), ACT_OK)
        self.assertEqual(act2.status(), ACT_OK)
        self.assertEqual(grp2.status(), ACT_OK)

    def test_group_dep_error(self):
        """A ok group which depends on an error group is on error"""
        grp1 = ActionGroup()
        act1 = TestAction('/bin/false')
        grp1.add(act1)
        grp2 = ActionGroup()
        act2 = TestAction('/bin/true')
        grp2.add(act2)

        grp2.depends_on(grp1)

        grp2.launch()
        task_self().run()

        self.assertEqual(act1.status(), ACT_ERROR)
        self.assertEqual(grp1.status(), ACT_ERROR)
        self.assertEqual(act2.status(), ACT_WAITING)
        self.assertEqual(grp2.status(), ACT_ERROR)
