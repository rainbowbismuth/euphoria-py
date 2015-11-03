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
import tiny_agent


class Counter(Agent):
    def __init__(self, loop=None):
        super(Counter, self).__init__(loop=loop)
        self._counter = 0

    @tiny_agent.send
    async def increment(self):
        self._counter += 1

    @tiny_agent.call
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


def test_linked_task_successful():
    loop = asyncio.get_event_loop()
    agent = Agent(loop=loop)

    async def mini_task():
        await asyncio.sleep(0.05)
        return

    async def task():
        mini = agent.spawn_linked_task(mini_task())
        await asyncio.sleep(0.10)
        assert mini.exited, "this tiny task should have exited 0.05 seconds ago"
        assert agent.alive, "it should have unlinked to keep the main task alive when it finished successfully"

    loop.run_until_complete(task())


def test_linked_task_failure():
    loop = asyncio.get_event_loop()
    agent = Agent(loop=loop)

    async def mini_bomb():
        await asyncio.sleep(0.05)
        raise Exception("ka-boom!")

    async def task():
        mini = agent.spawn_linked_task(mini_bomb())
        await asyncio.sleep(0.10)
        assert mini.exited, "we exploded"
        assert agent.exited, "our linked task should have taken us down too"

    loop.run_until_complete(task())