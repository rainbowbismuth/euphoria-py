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

from tiny_agent import Agent


class Counter(Agent):
    def __init__(self, loop=None):
        super(Counter, self).__init__(loop=loop)
        self._counter = 0

    @Agent.send
    async def increment(self):
        self._counter += 1

    @Agent.call
    async def current(self) -> int:
        return self._counter


def test_counter():
    loop = asyncio.get_event_loop()
    counter = Counter(loop=loop)
    async def task():
        counter.increment()
        counter.increment()
        counter.increment()
        result = await counter.current()
        assert result == 3, "we incremented three times"
    loop.run_until_complete(task())
