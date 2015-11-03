# euphoria-py
# Copyright (C) 2015  Emily A. Bellows
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

"""Implements the !ping, !uptime, !kill, and !restart from https://github.com/jedevc/botrulez"""

import datetime
import re

import tiny_agent
from euphoria import Bot, Packet
from tiny_agent import Agent


class Service(Agent):
    def __init__(self, bot: Bot, _: dict):
        super(Service, self).__init__(loop=bot.loop)
        bot.add_listener(self)
        self._bot = bot

        self._ping_re = re.compile("!ping @(.*)")
        self._uptime_re = re.compile("!uptime @(.*)")
        self._kill_re = re.compile("!kill @(.*)")
        self._restart_re = re.compile("!restart @(.*)")

    @tiny_agent.send
    async def on_packet(self, packet: Packet):
        send_event = packet.send_event
        if not send_event:
            return

        ping_match = self._ping_re.match(send_event.content)
        if ping_match:
            if ping_match.group(1) == self._bot.current_nick:
                await self._bot.send_content("pong!", parent=send_event.id)
            return

        uptime_match = self._uptime_re.match(send_event.content)
        if uptime_match:
            if uptime_match.group(1) != self._bot.current_nick:
                return

            now = datetime.datetime.now()
            diff = now - self._bot.start_time
            await self._bot.send_content("/me has been up since {0} ({1})".format(self._bot.start_time.ctime(),
                                                                                  str(diff)), parent=send_event.id)
            return

        kill_match = self._kill_re.match(send_event.content)
        if kill_match:
            if kill_match.group(1) == self._bot.current_nick:
                self._bot.exit()
                return

        restart_match = self._restart_re.match(send_event.content)
        if restart_match:
            if restart_match.group(1) == self._bot.current_nick:
                self._bot.exit()
                return
