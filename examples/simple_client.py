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
import logging

import euphoria

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()
room = input("room name> ")
passcode = input("passcode> ")
bot = euphoria.Client(room, loop=loop)


async def main_task():
    stream = bot.stream()
    await stream.skip_until(euphoria.HelloEvent)
    logging.info("We're connected, hello-event received!")

    try:
        await authenticate()
    except asyncio.CancelledError:
        logging.info("We're done here")


async def authenticate():
    auth_reply = await bot.send_auth(passcode)
    if not auth_reply.data.success:
        logging.error("Failed to authenticate")
        bot.close()
        return

    logging.info("Authenticated")

    nick_reply = await bot.send_nick("simple_bot")
    if nick_reply.error:
        logging.error("Failed to set nick: {0}".format(nick_reply.error))
        bot.close()
        return

    logging.info("Nick set")
    await send_event_loop()


async def send_event_loop():
    stream = bot.stream()
    while True:
        send_event = await stream.skip_until(euphoria.SendEvent)
        logging.info("{0}: {1}".format(
            send_event.data.sender.name, send_event.data.content))
        if send_event.data.content == "!quit":
            bot.close()
            return


loop.create_task(main_task())
loop.run_until_complete(bot.start())
