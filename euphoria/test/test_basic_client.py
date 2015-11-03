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
from asyncio import AbstractEventLoop

import tiny_agent
from euphoria import Client, Packet
from tiny_agent import Agent


class Basic(Agent):
    def __init__(self, client: Client, loop: AbstractEventLoop = None):
        super(Basic, self).__init__(loop=loop)
        self._client = client
        self._client.add_listener(self)

    @tiny_agent.send
    async def on_packet(self, packet: Packet):
        hello_event = packet.hello_event
        if hello_event:
            print("Hello, hello-event!")
            if hello_event.room_is_private:
                print("Goodbye, password-protected world!")
            else:
                print("Room isn't private, let's try to set our nick!")
                packet = await self._client.send_nick("basic-client-bot")
                if packet.error:
                    print("Oh no our nick was invalid because: {0}".format(packet.error))
                else:
                    nick_reply = packet.nick_reply
                    print("We did it! Our new nick is: {0}".format(nick_reply.to))
            return self.exit()


def test_main():
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()

    client = Client(room="test", loop=loop)
    basic = Basic(client, loop=loop)
    basic.bidirectional_link(client)  # Execute both client and basic until either of them stops.
    client.connect()

    loop.run_until_complete(asyncio.wait([client.task, basic.task]))  # Wait on both
    loop.run_until_complete(asyncio.wait(asyncio.Task.all_tasks(loop=loop)))  # Let everything else shutdown cleanly


if __name__ == '__main__':
    test_main()
