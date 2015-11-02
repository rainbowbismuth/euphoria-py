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
from typing import Optional

from tiny_agent import Agent, SupervisorOneForOne, SupervisorOneForAll, Restart, TooManyRestarts


class Bomb(Agent):
    def __init__(self, loop=None):
        super(Bomb, self).__init__(loop=loop)

    @Agent.send
    async def explode(self):
        raise Exception("boom!")


def test_one_for_one():
    loop = asyncio.get_event_loop()
    one_for_one = SupervisorOneForOne(loop=loop)
    one_for_one.add_child("bomb", lambda: Bomb(loop=loop))
    one_for_one.add_child("fragile", lambda: Agent(loop=loop))

    async def task():
        bomb = await one_for_one.get("bomb")
        fragile = await one_for_one.get("fragile")
        bomb.explode()

        while bomb.alive:
            await asyncio.sleep(0)  # lets sleep until the bomb gets that message

        assert fragile.alive, "our fragile should be okay because its a one-for-one supervisor"
        new_bomb = await one_for_one.get("bomb")
        assert new_bomb.alive, "we should have a new bomb that hasn't exploded"

    loop.run_until_complete(task())


def test_one_for_one_period_reset():
    loop = asyncio.get_event_loop()
    one_for_one = SupervisorOneForOne(max_restarts=1, period=0.15, loop=loop)
    one_for_one.add_child("bomb", lambda: Bomb(loop=loop))

    async def task():
        bomb = await one_for_one.get("bomb")
        bomb.explode()
        await asyncio.sleep(0.20)
        bomb = await one_for_one.get("bomb")
        bomb.explode()
        await asyncio.sleep(0.20)
        bomb = await one_for_one.get("bomb")
        bomb.explode()
        await asyncio.sleep(0.20)
        assert one_for_one.alive, "we're not dead because the period elapses and resets the restart counter"

    loop.run_until_complete(task())


def test_one_for_one_period_failure():
    loop = asyncio.get_event_loop()
    one_for_one = SupervisorOneForOne(max_restarts=1, period=0.15, loop=loop)
    one_for_one.add_child("bomb", lambda: Bomb(loop=loop))

    async def task():
        bomb = await one_for_one.get("bomb")
        bomb.explode()
        await asyncio.sleep(0.10)
        bomb = await one_for_one.get("bomb")
        bomb.explode()
        await asyncio.sleep(0.10)
        assert one_for_one.exited, "we're dead because we exploded twice too fast."

    loop.run_until_complete(task())

class RestartOnly(Agent):
    def __init__(self, loop=None):
        super(RestartOnly, self).__init__(loop=loop)

    def exit(self, exc: Optional[Exception] = None):
        assert isinstance(exc, Restart), "this agent must die to restarts"
        super(RestartOnly, self).exit(exc)


def test_one_for_all():
    loop = asyncio.get_event_loop()
    one_for_all = SupervisorOneForAll(loop=loop)
    one_for_all.add_child("bomb", lambda: Bomb(loop=loop))
    one_for_all.add_child("fragile", lambda: RestartOnly(loop=loop))

    async def task():
        bomb = await one_for_all.get("bomb")
        fragile = await one_for_all.get("fragile")
        bomb.explode()

        while bomb.alive:
            await asyncio.sleep(0)  # lets sleep until the bomb gets that message

        assert fragile.exited, "our fragile should be dead because its a one-for-all supervisor"
        new_bomb = await one_for_all.get("bomb")
        new_fragile = await one_for_all.get("fragile")
        assert new_bomb.alive, "we should have a new bomb that hasn't exploded"
        assert new_fragile.alive, "and a new fragile that hasn't shattered"

    loop.run_until_complete(task())


class TooManyRestartsOnly(SupervisorOneForAll):
    def __init__(self, loop=None):
        super(TooManyRestartsOnly, self).__init__(loop=loop)

    def exit(self, exc: Optional[Exception] = None):
        assert isinstance(exc, TooManyRestarts), "this agent must die from too many restarts"
        super(TooManyRestartsOnly, self).exit(exc)


def test_too_many_resets():
    loop = asyncio.get_event_loop()
    one_for_all = TooManyRestartsOnly(loop=loop)
    one_for_all.add_child("bomb", lambda: Bomb(loop=loop))

    async def task():
        while not one_for_all.exited:
            bomb = await one_for_all.get("bomb")
            if bomb and bomb.alive:
                bomb.explode()

    loop.run_until_complete(asyncio.wait_for(task(), timeout=3.0, loop=loop))
