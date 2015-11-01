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
from euphoria.state_machines import NickAndAuth

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()

client = euphoria.Client(input("room name> "), loop=loop)

nick_and_auth = NickAndAuth(client, "nick_and_auth_client")
nick_and_auth.passcode = input("passcode> ")


async def send_event_loop():
    stream = client.stream()
    while True:
        await nick_and_auth.wait_for_auth()

        send_event = await stream.skip_until(euphoria.SendEvent)
        logging.info("%s: %s", send_event.data.sender.name,
                     send_event.data.content)

        if send_event.data.content == "!quit":
            await client.send("goodbye!", parent=send_event.data.id)
            client.close()
            return

        elif send_event.data.content[0:5] == "!nick":
            nick_and_auth.desired_nick = send_event.data.content[6:]


async def boot():
    await nick_and_auth.start()
    loop.create_task(send_event_loop())
    await client.start()


loop.run_until_complete(boot())
