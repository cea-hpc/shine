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


"""shine-HA slack notification"""

import json
import logging
import requests
import time

from ClusterShell.NodeSet import NodeSet
import Shine.CLI.Display as Display
from Shine.CLI.TextTable import TextTable
from Shine.HA.alerts import Alert, ALERT_CLS_FS, ALERT_CLS_LNET
from Shine.HA.fsmon import STATE_IDTXT_MAP

# HTML colors from Slack logo
COLOR_GREEN = '#30AF7E'
COLOR_YELLOW = '#E49A00'
COLOR_LIGHT_BLUE = '#5BBFD5'
COLOR_GREEN_BLUE = '#15836A'
COLOR_DARK_RED = '#29092B'
COLOR_PINK = '#D7004F'
COLOR_RED = '#C20000'

LOGGER = logging.getLogger(__name__)


class SlackWebhookAlert(Alert):

    def __init__(self, webhook_url, channel, bot_username, bot_emoji):
        Alert.__init__(self, 'slack')
        self.webhook_url = webhook_url
        self.channel = channel
        self.bot_username = bot_username
        self.bot_emoji = bot_emoji

    def post_attachment(self, subject, fields, color="#316cba"):
        """"""
        now = time.time()
        payload = {"text": subject,
                   "fallback": subject,
                   "channel": self.channel,
                   "username": self.bot_username,
                   "icon_emoji": self.bot_emoji,
                   "attachments": [{"color": color,
                                    "fields": fields,
                                    "ts": now}]}
        res = requests.post(self.webhook_url, data=json.dumps(payload))
        if res.status_code != requests.codes.ok:
            LOGGER.info("reply: " + res.text)
            return 1
        return 0

    def info(self, aclass, message, ctx=None):
        if aclass == ALERT_CLS_FS:
            self._fs_info(message, ctx, ':postal_horn:', COLOR_GREEN)
        elif aclass == ALERT_CLS_LNET:
            LOGGER.debug('info ALERT_CLS_LNET %s %s', message, ctx)
            self._lnet_info(message, ctx, ':satellite_antenna:', COLOR_GREEN)

    def warning(self, aclass, message, ctx=None):
        if aclass == ALERT_CLS_FS:
            self._fs_error(message, ctx, ':warning:', COLOR_YELLOW)
        elif aclass == ALERT_CLS_LNET:
            LOGGER.debug('warning ALERT_CLS_LNET %s %s', message, ctx)
            self._lnet_error(message, ctx, ':warning:', COLOR_YELLOW)

    def critical(self, aclass, message, ctx=None):
        if aclass == ALERT_CLS_FS:
            self._fs_error(message, ctx, ':rotating_light:', COLOR_RED)
        elif aclass == ALERT_CLS_LNET:
            LOGGER.debug('critical ALERT_CLS_LNET %s %s', message, ctx)
            self._lnet_error(message, ctx, ':rotating_light:', COLOR_RED)

    def _fs_info(self, message, ctx, emoji, color):
        # Create table with wanted parameters
        tbl = TextTable("%status %labels %count %type")
        # Feed table directly from Shine FileSystem instance
        Display.table_fill(tbl, ctx['FileSystem'])
        fields = []
        for row in tbl:
            fields.append({"title": '%s (%s)' % (row['labels'], row['count']),
                           "value": row['status'],
                           "short": True})
        self.post_attachment(emoji + ' ' + message, fields, color=color)

    def _fs_error(self, message, ctx, emoji, color):
        comp_st_cnt_list = ctx['comp_st_cnt_list']
        targets = NodeSet.fromlist(scobj.comp.uniqueid()
                                   for scobj in comp_st_cnt_list)
        status = NodeSet.fromlist(STATE_IDTXT_MAP[scobj.state]
                                  for scobj in comp_st_cnt_list)
        title = "Components (%d)" % len(comp_st_cnt_list)
        fields = [{"title": title, "value": str(targets), "short": True},
                  {"title": "Status", "value": ','.join(status), "short": True}]
        self.post_attachment(emoji + ' ' + message, fields, color=color)

    def _lnet_error(self, message, ctx, emoji, color):
        nodeset = NodeSet.fromlist(ctx['nodelist'])
        nids = NodeSet()
        for nidss in ctx['down_cnt_list']:
            nids.updaten(nidss.nids())
        LOGGER.debug('SlackWebhookAlert._lnet_error: %s', nodeset)
        fields = [{"title": "Servers", "value": str(nodeset), "short": True},
                  {"title": 'NIDs', 'value': str(nids), "short": True}]
        self.post_attachment(emoji + ' ' + message, fields, color=color)

    def _lnet_info(self, message, ctx, emoji, color):
        if 'nodelist' in ctx and 'down_cnt_list' in ctx:
            self._lnet_error(message, ctx, ":satellite_antenna:", COLOR_GREEN)
        else:
            self.post_attachment(emoji + ' ' + message, [], color=color)

ALERT_CLASS = SlackWebhookAlert
