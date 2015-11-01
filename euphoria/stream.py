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

"""Contains a class that makes it easy to process streams of packets"""

import asyncio
from asyncio import AbstractEventLoop
from typing import Callable

from .data import Packet

__all__ = ['Stream']


class Stream:
    """A stream of packets from a single Client.

    :param asyncio.BaseEventLoop loop: The asyncio event loop you want to use"""

    def __init__(self, loop: AbstractEventLoop = None):
        self._loop = loop
        self._connected = asyncio.Event(loop=loop)
        self._closed = False
        self._queue = asyncio.Queue(loop=loop)
        self._waiting_on = None

    def _connect(self):
        if not self._closed:
            self._connected.set()

    def _send(self, packet: Packet) -> None:
        # This is used by Client's receive loop to put an item into the Stream.
        assert not self._closed
        assert self._connected.is_set()
        self._queue.put_nowait(packet)

    def close(self) -> None:
        """Closes this stream. Will not receive any more messages from the Client."""
        self._connected.clear()
        self._closed = True
        if self._waiting_on:
            # If there's somebody waiting inside a Stream.any() we have to
            # cancel them because no more messages are coming.
            self._waiting_on.cancel()

    @property
    def loop(self) -> AbstractEventLoop:
        """The asyncio event loop this Stream uses.

        :rtype: asyncio.BaseEventLoop"""
        return self._loop

    @property
    def connected(self) -> bool:
        """Returns whether this stream can receive messages from the Client.

        :rtype: bool"""
        return self._connected.is_set()

    @property
    def open(self) -> bool:
        """Returns whether this stream is connected and not closed.

        :rtype: bool"""
        return self._connected.is_set() and not self._closed

    @property
    def closed(self) -> bool:
        """Returns whether this stream has been closed.

        :rtype: bool"""
        return self._closed

    def empty(self) -> bool:
        """Returns whether or not the Stream is currently empty.

        :rtype: bool"""
        return self._queue.empty()

    async def wait_until_connected(self):
        await self._connected.wait()

    async def any(self) -> Packet:
        """Returns the next message from the Client.

        This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_.

        :rtype: euphoria.Packet
        :raises asyncio.CancelledError: if the client is closed"""
        # Only one coroutine should be using a stream, so if self._waiting_on
        # isn't None, then clearly more then one coroutine is using it.
        assert self._waiting_on is None

        await self.wait_until_connected()

        if self._closed:
            raise asyncio.CancelledError

        self._waiting_on = asyncio.ensure_future(
            self._queue.get(), loop=self._loop)
        try:
            result = await self._waiting_on
            return result
        finally:
            self._waiting_on = None

    async def skip_until_type(self, type_: type) -> Packet:
        return await self.skip_until(lambda p: p.is_type(type_))

    async def skip_until(self, condition: Callable[[Packet], bool]) -> Packet:
        """Discards messages in this stream until one matches condition.

        This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_.

        :param condition: Skip packets until condition(packet) == True
        :rtype: euphoria.Packet
        :raises asyncio.CancelledError: if the client is closed"""
        while True:
            packet = await self.any()
            if not condition(packet):
                continue
            return packet

    async def select_type(self, type_: type) -> Packet:
        return await self.select(lambda p: p.is_type(type_))

    async def select(self, condition: Callable[[Packet], bool]) -> Packet:
        """Finds a message in this stream matching the given condition, without
         discarding the rest of them.

         This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_.

         :param condition: Skip packets until condition(packet) == True
         :rtype: euphoria.Packet
         :raises asyncio.CancelledError: if the client is closed"""
        while True:
            packet = await self.any()
            if not condition(packet):
                self._queue.put_nowait(packet)
                continue

            return packet
