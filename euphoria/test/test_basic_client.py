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
from asyncio import Queue
from euphoria import connect, links, raise_early_exit_on_done, EarlyExit, Packet, SendQueue


@raise_early_exit_on_done
async def basic(send: SendQueue, recv: Queue):
    packet = await recv.get()  # type: Packet
    hello_event = packet.hello_event
    if hello_event:
        print("Hello, hello-event!")
        if hello_event.room_is_private:
            print("Goodbye, password-protected world!")
        else:
            print("Room isn't private, let's try to set our nick!")
            packet = await send.send_nick("basic-client-bot")  # type: Packet
            if packet.error:
                print("Oh no our nick was invalid because: {0}".format(packet.error))
            else:
                nick_reply = packet.nick_reply
                print("We did it! Our new nick is: {0}".format(nick_reply.to))


def test_main():
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()

    async def main_task():
        (connected, send, recv) = connect(room="test", loop=loop)
        basic_task = asyncio.ensure_future(basic(send, recv), loop=loop)
        try:
            await links([connected, basic_task])
        except EarlyExit:
            pass

    loop.run_until_complete(asyncio.ensure_future(main_task(), loop=loop))


if __name__ == '__main__':
    test_main()
