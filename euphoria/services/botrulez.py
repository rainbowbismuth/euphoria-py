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

import sys
import re
import datetime
from euphoria import SendEvent, Bot


async def main(bot: Bot):
    """Entry point into the botrulez service.

    This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_.

    :param euphoria.Bot bot: This service's bot"""
    ping_re = re.compile("!ping @(.*)")
    uptime_re = re.compile("!uptime @(.*)")
    kill_re = re.compile("!kill @(.*)")
    restart_re = re.compile("!restart @(.*)")

    client = bot.client
    stream = client.stream()
    while True:
        packet = await stream.skip_until(SendEvent)
        send_event = packet.send_event

        ping_match = ping_re.match(send_event.content)
        if ping_match:
            if not ping_match.group(1) == bot.nick_and_auth.current_nick:
                continue
            client.send("pong!", parent=send_event.id)
            continue

        uptime_match = uptime_re.match(send_event.content)
        if uptime_match:
            if not uptime_match.group(1) == bot.nick_and_auth.current_nick:
                continue
            now = datetime.datetime.now()
            diff = now - bot.start_time
            client.send("/me has been up since {0} ({1})".format(bot.start_time.ctime(), str(diff)),
                        parent=send_event.id)
            continue

        kill_match = kill_re.match(send_event.content)
        if kill_match:
            if not kill_match.group(1) == bot.nick_and_auth.current_nick:
                continue
            sys.exit()

        restart_match = restart_re.match(send_event.content)
        if restart_match:
            if not restart_match.group(1) == bot.nick_and_auth.current_nick:
                continue
            bot.restart()
