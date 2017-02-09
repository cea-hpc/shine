#
# Copyright (C) 2017 Board of Trustees, Leland Stanford Jr. University
#
# Written by Stephane Thiell <sthiell@stanford.edu>
#
#   --*-*- Stanford University Research Computing Center -*-*--
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Lustre Shine HA - File System Actions"""

import logging
from threading import Thread

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import task_terminate

from Shine.Configuration.FileSystem import ModelFileIOError
import Shine.FSUtils as FSUtils


LOGGER = logging.getLogger(__name__)


class StatusThread(Thread):
    """
    Thread used by shine-HA to get the status of the filesystem using Shine API.
    """
    def __init__(self, fs_name, reply_port):
        Thread.__init__(self)
        self.fs_name = fs_name
        self.reply_port = reply_port

    def run(self):
        # Get only status of targets for now
        try:
            fs_conf, fs = FSUtils.open_lustrefs(self.fs_name, 'mgt,mdt,ost')
        except ModelFileIOError as exc:
            LOGGER.error('StatusThread: %s' % exc)
            self.reply_port.msg_send(('abort', None, None))
            return

        comps = fs.components.filter(supports='index')

        fs_result = fs.status(comps, extended=True)
        LOGGER.debug('StatusThread: fs.status=%s', fs_result)

        for msg, nodelist in fs.proxy_errors.walk():
            nodeset = NodeSet.fromlist(nodelist)
            LOGGER.error("StatusThread: proxy error msg from %s: %s", nodeset,
                         msg)

        self.reply_port.msg_send(('status', fs_conf, fs))
        task_terminate()


class StartThread(Thread):
    """
    Thread used by shine-HA to start failover targets using Shine API.
    """
    def __init__(self, fs_name, reply_port, comps, failover=None):
        Thread.__init__(self)
        self.fs_name = fs_name
        self.reply_port = reply_port
        self.comps = comps # ComponentGroup
        self.failover = failover

    def run(self):
        try:
            fs_conf, fs = FSUtils.open_lustrefs(self.fs_name, 'mgt,mdt,ost')
        except ModelFileIOError as exc:
            LOGGER.error('StartThread: %s' % exc)
            self.reply_port.msg_send(('abort', None, None))
            return

        fs_result = fs.start(self.comps, failover=self.failover)
        LOGGER.debug('StartThread: fs.status=%s', fs_result)

        for msg, nodelist in fs.proxy_errors.walk():
            nodeset = NodeSet.fromlist(nodelist)
            LOGGER.error("StartThread: proxy error msg from %s: %s", nodeset,
                         msg)

        self.reply_port.msg_send(('start', self.fs_name, self.comps, fs_result))
        task_terminate()
