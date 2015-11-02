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
from euphoria import Client, NickAndAuth


def test_main():
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()

    client = Client(room="test", loop=loop)
    nick_and_auth = NickAndAuth(client, "nick-and-auth-bot", loop=loop)
    nick_and_auth.bidirectional_link(client)  # Execute both client and nick_and_auth until either of them stops.
    client.connect()

    nick_cell = [nick_and_auth.current_nick]

    async def task():
        while nick_and_auth.current_nick != nick_and_auth.desired_nick:
            await asyncio.sleep(0.0)
            nick_cell[0] = nick_and_auth.current_nick

    checker = asyncio.wait_for(task(), timeout=3.0, loop=loop)
    loop.run_until_complete(asyncio.wait([client.task, nick_and_auth.task, checker],
                                         return_when=asyncio.FIRST_COMPLETED))  # Wait on all three
    client.exit()  # Exit if it didn't crash
    nick_and_auth.exit()  # Exit if it didn't crash
    loop.run_until_complete(asyncio.wait(asyncio.Task.all_tasks(loop=loop)))  # Let everything else shutdown cleanly
    assert nick_cell[0] == nick_and_auth.desired_nick, "after all of this I hope we got to set our nick"


if __name__ == '__main__':
    test_main()
