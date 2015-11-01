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

from euphoria import SendEvent, Bot


async def main(bot: Bot):
    """Entry point into the !nick' service.

    This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_.

    :param euphoria.Bot bot: This service's bot"""
    client = bot.client
    nick_and_auth = bot.nick_and_auth
    stream = client.stream()
    while True:
        packet = await stream.skip_until(SendEvent)
        send_event = packet.send_event
        if send_event.content[0:5] == "!nick":
            error = await nick_and_auth.set_desired_nick(send_event.content[6:])
            if error:
                client.send("error: {0}".format(error), parent=send_event.id)
