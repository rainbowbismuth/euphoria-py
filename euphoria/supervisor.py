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

"""A small asyncio utility to restart tasks on failure"""

import asyncio
from asyncio import AbstractEventLoop, Event, CancelledError

__all__ = ['links', 'retry_supervisor']


async def links(co_routines: list, loop: AbstractEventLoop = None):
    (done, remaining) = await asyncio.wait(co_routines, loop=loop, return_when=asyncio.FIRST_EXCEPTION)
    for task in remaining:
        task.cancel()
    for task in done:
        exc = task.exception()
        if exc:
            raise exc


async def retry_supervisor(coro_factories: list, max_retries: int = 3, reset_timer: float = 60.0,
                           loop: AbstractEventLoop = None):
    failure_ev = Event(loop=loop)
    retries_ref = [0]

    async def try_coro(coro_factory):
        while True:
            # noinspection PyBroadException
            try:
                await coro_factory()
            except CancelledError:
                raise
            except Exception:
                failure_ev.set()
                retries_ref[0] += 1
                if retries_ref[0] > max_retries:
                    raise
            else:
                return

    async def reset_retries():
        while True:
            failure_ev.wait()
            await asyncio.sleep(reset_timer)
            retries_ref[0] = 0
            failure_ev.clear()

    all_children = list(map(lambda f: asyncio.ensure_future(try_coro(f), loop=loop), coro_factories))
    reset_task = asyncio.ensure_future(reset_retries(), loop=loop)
    try:
        await links(all_children, loop=loop)
    finally:
        reset_task.cancel()


# TODO: Move these tests in euphoria/test


def test_retry_supervisor_no_retries():
    loop = asyncio.get_event_loop()
    count_ref = [0]

    async def increment_count():
        count_ref[0] += 1

    async def main_task():
        await retry_supervisor([increment_count, increment_count, increment_count], loop=loop)

    loop.run_until_complete(asyncio.ensure_future(main_task(), loop=loop))
    assert count_ref[0] == 3, "we should have incremented 3 times successfully"


def test_retry_supervisor_with_retries():
    loop = asyncio.get_event_loop()
    count_ref = [0]

    async def increment_count():
        if count_ref[0] >= 3:
            return
        count_ref[0] += 1
        raise Exception("roar")

    async def main_task():
        await retry_supervisor([increment_count], max_retries=5, loop=loop)

    loop.run_until_complete(asyncio.ensure_future(main_task(), loop=loop))
    assert count_ref[0] == 3, "we should have incremented 3 times successfully"


def test_retry_supervisor_break():
    loop = asyncio.get_event_loop()
    caught_exec_ref = [False]

    async def explode():
        raise NotImplementedError

    async def main_task():
        try:
            await retry_supervisor([explode])
        except NotImplementedError:
            caught_exec_ref[0] = True

    loop.run_until_complete(asyncio.ensure_future(main_task(), loop=loop))
    assert caught_exec_ref[0] == True, "we should have caught a NotImplementedError after some retries"
