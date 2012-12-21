# Fsck.py -- Lustre action class: fsck
# Copyright (C) 2010-2012 CEA
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

"""
Action class to check (fsck) target filesystem coherency.
"""

import time
import logging

from Shine.Lustre.Actions.Action import Action, FSAction, Result, ErrorResult
from Shine.Lustre.Component import TARGET_ERROR

class FsckProgress(Result):
    """
    Result message sent with 'progress' event, to provide fsck command
    progression.
    """

    # Number of passes in a e2fsck run.
    _NB_PASSES = 5

    def __init__(self, passid, current, total):
        Result.__init__(self)
        self.pass_id = int(passid)
        self.pass_progress = float(current) / float(total)

    @property
    def progress(self):
        """Current fsck command progression value, between 1 and 100."""
        return ((self.pass_id - 1 + self.pass_progress) / self._NB_PASSES) * 100

class Fsck(FSAction):
    """
    File system check using 'e2fsck'.
    """

    NAME = 'fsck'

    def __init__(self, target, **kwargs):
        FSAction.__init__(self, target, **kwargs)

        # e2fsck send its progression on stderr
        self.stderr = True

        # Logging
        self.logger = logging.getLogger(__name__)

        # To track message rate
        self._last_progress = 0

    def _prepare_cmd(self):
        """
        Create the command line to run 'e2fsck'.
        """
        command = ["e2fsck", '-f -y -C2', self.comp.dev]

        # Process additional options
        if self.addopts:
            command.append(self.addopts)

        return command

    def launch(self):
        FSAction.launch(self)
        self.logger.info("%-16s %s" % (self.comp.label, "Starting fsck"))

    def ev_read(self, worker):
        self.logger.info("%-16s %s" % (self.comp.label, worker.current_msg))

    def ev_error(self, worker):
        FSAction.ev_error(self, worker)
        try:
            line = worker.current_errmsg
            passid, current, total, dummy = line.split(' ', 3)

            result = FsckProgress(passid, current, total)
            # Limit message rate to one message per second max.
            if result.progress == 100 or self._last_progress + 1 < time.time():
                self._last_progress = time.time()
                self.comp._action_progress(self.NAME, result=result)

        except ValueError:
            pass

    def ev_close(self, worker):
        """
        Check process termination status and generate appropriate events.

        Note that if fsck has correctly fixed some errors, actions will be
        considered as successful.
        """
        # We want to skiping FSAction.ev_close(), just call the upper layer.
        Action.ev_close(self, worker)

        self.comp.lustre_check()

        if worker.did_timeout():
            # action timed out
            self.comp._action_timeout('fsck')
        # fsck returns 0=NOERROR, 1=OK_BUT_CORRECTION, 2=OK_BUT_REBOOT.
        # see man fsck.
        elif worker.retcode() in (0, 1, 2):
            # action succeeded
            result = Result(duration=self.duration, retcode=worker.retcode())
            if worker.retcode() in (1, 2):
                result.message = "Errors corrected"
            self.comp._action_done('fsck', result)
        else:
            # action failure
            self.comp.state = TARGET_ERROR
            result = ErrorResult(worker.read(), self.duration, worker.retcode())
            self.comp._action_failed('fsck', result)
