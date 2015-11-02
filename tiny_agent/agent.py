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
from asyncio import AbstractEventLoop, Queue, Future
from typing import Optional
from weakref import WeakSet

__all__ = ['Agent']

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

            if not self.exited:
                self._queue.put_nowait(do_it)

        return send_wrapper

    @classmethod
    def call(cls, f):
        def call_wrapper(self: 'Agent', *args, **kwargs) -> Future:
            future = Future(loop=self._loop)

            async def do_it():
                x = await f(self, *args, **kwargs)
                future.set_result(x)

            if not self.exited:
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
    def loop(self) -> bool:
        return self._loop

    def bidirectional_link(self, to: 'Agent'):
        self._links.add(to)
        to._links.add(self)

    def monitor(self, monitored: 'Agent'):
        self._links.add(monitored)
        monitored._monitors.add(self)

    async def _main(self):
        # noinspection PyBroadException
        try:
            while True:
                fun = await self._queue.get()
                await fun()
        except Exception as exc:
            self.exit(exc)
        else:
            self.exit(None)

    def exit(self, exc: Optional[Exception] = None):
        try:
            if self.exited:
                return
            logger.debug("%s is exiting because %s", self, exc)
            for link in self._links:
                link.exit(exc)

            for monitor in self._monitors:
                method = getattr(monitor, 'on_monitored_exit', None)
                if method:
                    method(self, exc)
                else:
                    logger.warning("%s was monitoring an agent %s, but doesn't implemented on_monitored_exit",
                                   monitor, self)

            self._task.cancel()
        finally:
            self._links = WeakSet()
            self._monitors = WeakSet()
            self._task = None
