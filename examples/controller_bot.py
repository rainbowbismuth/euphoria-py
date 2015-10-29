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

import asyncio
import euphoria
import euphoria.controller as ctlr
import logging

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()
room = input("room name> ")
passcode = input("passcode> ")
bot = euphoria.Client(room, loop=loop)

nick_and_auth_ctlr = ctlr.NickAndAuthController(
    bot, "controller_bot", passcode)
ping_ctlr = ctlr.PingController(bot)

async def send_event_loop():
    stream = await bot.stream()
    while True:
        send_event = await stream.skip_until(euphoria.SendEvent)
        print("{0}: {1}".format(
            send_event.data.sender.name, send_event.data.content))
        if send_event.data.content == "!quit":
            await bot.close()
            return

async def main_task():
    bot_start = asyncio.ensure_future(bot.start())
    ping_start = asyncio.ensure_future(ping_ctlr.start())
    nick_and_auth_start = asyncio.ensure_future(nick_and_auth_ctlr.start())
    send_start = asyncio.ensure_future(send_event_loop())

    task_list = [bot_start, ping_start, nick_and_auth_start, send_start]
    (_, pending) = await asyncio.wait(task_list,
                                      return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()

loop.run_until_complete(main_task())
