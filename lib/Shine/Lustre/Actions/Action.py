# Action.py -- Abstract class for shine lustre action
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

from ClusterShell.Event import EventHandler

class ActionException(Exception):
    def __init__(self, rc, message):
        self.rc = rc
        self.message = message

    def get_rc(self):
        return self.rc

    def __str__(self):
        return self.message

class ActionErrorException(ActionException):
    pass

class ActionWarningException(ActionException):
    pass

class ActionFailedError(ActionErrorException):
    pass


class Action(EventHandler):
    """
    Astract shine action class.
    """

    def __init__(self, task):
        EventHandler.__init__(self)
        self.task = task

    #
    # Public (virtual) method to implement
    #
    def launch(self):
        raise NotImplementedError("Derived classes must implement.")

    #
    # Public helper
    #
    def launch_and_run(self):
        self.launch()
        self.task.run()

