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
from asyncio import AbstractEventLoop, Queue, Future, Task
from typing import Optional
from weakref import WeakSet

__all__ = ['Agent', 'LinkedTask']

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, loop: AbstractEventLoop = None):
        self._loop = loop
        self._links = WeakSet()
        self._monitors = WeakSet()
        self._queue = Queue(loop=self._loop)
        self._task = asyncio.ensure_future(self._main(), loop=self._loop)

    @classmethod
    def send(cls, f):
        def send_wrapper(self: 'Agent', *args, **kwargs) -> None:
            async def do_it():
                result = await f(self, *args, **kwargs)
                if result is not None:
                    logger.warning("%s tried to return a result in a @Agent.send method, %s", self, f)

            if self.alive:
                self._queue.put_nowait(do_it)

        return send_wrapper

    @classmethod
    def call(cls, f):
        def call_wrapper(self: 'Agent', *args, **kwargs) -> Future:
            future = Future(loop=self._loop)

            async def do_it():
                x = await f(self, *args, **kwargs)
                future.set_result(x)

            if self.alive:
                self._queue.put_nowait(do_it)
            return future

        return call_wrapper

    @property
    def alive(self) -> bool:
        return self._task is not None

    @property
    def exited(self) -> bool:
        return self._task is None

    @property
    def loop(self) -> AbstractEventLoop:
        return self._loop

    @property
    def task(self) -> Task:
        return self._task

    def bidirectional_link(self, to: 'Agent'):
        self._links.add(to)
        to._links.add(self)

    def unlink(self, from_: 'Agent'):
        self._links.remove(from_)
        from_._links.remove(self)

    def monitor(self, monitored: 'Agent'):
        self._links.add(monitored)
        monitored._monitors.add(self)

    def spawn_linked_task(self, coro_or_future) -> 'LinkedTask':
        return LinkedTask(self, coro_or_future, loop=self._loop)

    async def _main(self):
        # noinspection PyBroadException
        try:
            while self.alive:
                fun = await self._queue.get()
                await fun()
        except Exception as exc:
            self.exit(exc)
        else:
            self.exit(None)

    def exit(self, exc: Optional[Exception] = None):
        old_task = self._task
        try:
            if self.exited:
                return
            self._task = None
            if exc:
                logger.debug("%s is exiting because %s", self, exc)
            else:
                logger.debug("%s is exiting normally", self)
            for link in self._links:
                link.exit(exc)

            for monitor in self._monitors:
                method = getattr(monitor, 'on_monitored_exit', None)
                if method:
                    method(self, exc)
                else:
                    logger.warning("%s was monitoring an agent %s, but doesn't implemented on_monitored_exit",
                                   monitor, self)
        finally:
            if old_task is not None:
                old_task.cancel()
                self._links = WeakSet()
                self._monitors = WeakSet()


class LinkedTask(Agent):
    def __init__(self, linked_to: Agent, coro_or_future, loop: AbstractEventLoop=None):
        super(LinkedTask, self).__init__(loop=loop)
        self.bidirectional_link(linked_to)
        async def do_it():
            try:
                result = await coro_or_future
                if result is not None:
                    logger.warning("%s tried to return a result from a LinkedTask, %s", coro_or_future, self)
                self.unlink(linked_to)  # We finished successfully so lets not kill our friend when we die
            finally:
                self.exit()
        self._queue.put_nowait(do_it)

