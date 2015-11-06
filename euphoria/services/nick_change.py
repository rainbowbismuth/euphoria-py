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

"""Say '!nick' new_nick to change the bots name to new_nick"""

import tiny_agent
from euphoria import Bot, Packet
from tiny_agent import Agent


class Service(Agent):
    @tiny_agent.init
    def __init__(self, bot: Bot, _: dict):
        super(Service, self).__init__(loop=bot.loop)
        bot.add_listener(self)
        self._bot = bot

    @tiny_agent.send
    async def on_packet(self, packet: Packet):
        send_event = packet.send_event
        if send_event and send_event.content.startswith("!nick"):
            error = await self._bot.set_desired_nick(send_event.content[6:])
            if error:
                self._bot.send_content(error, parent=send_event.id)
