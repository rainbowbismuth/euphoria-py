# TODO: Add docstring

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
from asyncio import BaseEventLoop
import inspect
from .exceptions import *
from .data import Packet

class Stream:
    # TODO: Add docstring

    def __init__(self, loop: BaseEventLoop=None):
        self._loop = loop
        self._client_open = True
        self._queue = asyncio.Queue(loop=loop)
        self._waiting_on = None

    def _send(self, packet: Packet) -> None:
        # This is used by Client's receive loop to put an item into the Stream.
        self._queue.put_nowait(packet)

    def close(self) -> None:
        """Closes this stream. Will not receive any more messages from the Client."""
        self._client_open = False
        if self._waiting_on:
            # If there's somebody waiting inside a Stream.any() we have to
            # cancel them because no more messages are coming.
            self._waiting_on.cancel()

    @property
    def loop(self) -> BaseEventLoop:
        """The asyncio event loop this Stream uses."""
        return self._loop

    @property
    def open(self) -> bool:
        """Returns whether this stream can receive messages from the Client."""
        return self._client_open

    def empty(self) -> bool:
        """Returns whether or not the Stream is currently empty."""
        return self._queue.empty()

    async def any(self) -> Packet:
        """Returns the next message from the Client."""
        # Only one coroutine should be using a stream, so if self._waiting_on
        # isn't None, then clearly more then one coroutine is using it.
        assert self._waiting_on is None

        if not self._client_open and self.empty():
            raise StreamEmpty("Stream is closed and empty.")

        self._waiting_on = asyncio.ensure_future(
            self._queue.get(), loop=self._loop)
        try:
            result = await self._waiting_on
            return result
        finally:
            self._waiting_on = None

    async def skip_until(self, condition) -> Packet:
        """Discards messages in this stream until one matches condition."""
        if inspect.isclass(condition):
            kls = condition
            # TODO: change this to a def instead of a lambda
            condition = lambda p: p.data and isinstance(p.data, kls)

        while True:
            packet = await self.any()
            if not condition(packet):
                continue
            return packet

    async def select(self, condition) -> Packet:
        """Finds a message in this stream matching the given condition, without
         discarding the rest of them."""
        if inspect.isclass(condition):
            kls = condition
            # TODO: change this to a def instead of a lambda
            condition = lambda p: p.data and isinstance(p.data, kls)

        while True:
            packet = await self.any()
            if not condition(packet):
                self._queue.put_nowait(packet)
                continue

            return packet
