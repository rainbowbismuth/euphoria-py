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

from euphoria import SendEvent, Bot, Client


async def chill_and_respond(client: Client, length: int, msg: str):
    await asyncio.sleep(length, loop=client.loop)
    if not client.closed:
        await client.send(msg)


async def main(bot: Bot):
    """Entry point into the '!remind' service.

    This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_.

    :param euphoria.Bot bot: This service's bot"""
    minute_re = re.compile("!remind (\d+)m (.*)")
    client = bot.client
    stream = client.stream()
    while True:
        packet = await stream.skip_until_type(SendEvent)
        send_event = packet.send_event

        if send_event.content.startswith("!remind"):
            match = minute_re.match(send_event.content)
            if match:
                minutes = float(match.group(1))
                msg = "reminder @{0}: {1}".format(send_event.sender.name, match.group(2))
                asyncio.ensure_future(chill_and_respond(client,
                                                        minutes * 60, msg))
                await client.send("acknowledged!", parent=send_event.id)
            else:
                await client.send("usage: !remind 15m go on a walk", parent=send_event.id)
        else:
            continue
