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
from euphoria.state_machines import NickAndAuth
import logging

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()

room = input("room name> ")
passcode = input("passcode> ")

client = euphoria.Client(room, loop=loop)

nick_and_auth = NickAndAuth(client, "nick_and_auth_client")
nick_and_auth.passcode = passcode

async def send_event_loop():
    stream = await client.stream()
    while True:
        await nick_and_auth.wait_for_auth()

        send_event = await stream.skip_until(euphoria.SendEvent)
        logging.info("%s: %s", send_event.data.sender.name,
                     send_event.data.content)

        if send_event.data.content == "!quit":
            await client.send("goodbye!", parent=send_event.data.id)
            client.close()
            return

loop.create_task(nick_and_auth.start())
loop.create_task(send_event_loop())
loop.run_until_complete(client.start())
