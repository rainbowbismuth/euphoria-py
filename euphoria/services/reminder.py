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

"""Say '!remind 15m eat food' to be reminded in 15 minutes to eat food"""

import asyncio
import re

import tiny_agent
from euphoria import Bot, Packet
from tiny_agent import Agent


async def chill_and_respond(bot: Bot, length: int, msg: str):
    await asyncio.sleep(length, loop=bot.loop)
    if bot.connected:
        bot.send_content(msg)


class Service(Agent):
    def __init__(self, bot: Bot, _: dict):
        super(Service, self).__init__(loop=bot.loop)
        bot.add_listener(self)
        self._bot = bot
        self._minute_re = re.compile("!remind (\d+)m (.*)")

    @tiny_agent.send
    async def on_packet(self, packet: Packet):
        send_event = packet.send_event
        if send_event and send_event.content.startswith("!remind"):
            match = self._minute_re.match(send_event.content)
            if match:
                minutes = float(match.group(1))
                msg = "reminder @{0}: {1}".format(send_event.sender.name, match.group(2))
                asyncio.ensure_future(chill_and_respond(self._bot, minutes * 60, msg), loop=self.loop)
                await self._bot.send_content("acknowledged!", parent=send_event.id)
            else:
                await self._bot.send_content("usage: !remind 15m go on a walk", parent=send_event.id)
