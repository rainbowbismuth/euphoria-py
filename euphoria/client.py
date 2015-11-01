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

"""Contains the class that lets you connect to an euphoria server"""

import asyncio
import json
import logging
import weakref
from asyncio import Future, AbstractEventLoop
from typing import Tuple

import websockets

from euphoria import Stream, Packet, PingEvent

__all__ = ['Client']

logger = logging.getLogger(__name__)

EUPHORIA_URL = "wss://euphoria.io:443/room/{0}/ws"


class Client:
    """A websocket client for Euphoria.

    :param str room: The room the client should join when started
    :param asyncio.AbstractEventLoop loop: The asyncio event loop you want to use
    """

    def __init__(self, room: str, uri_format: str = EUPHORIA_URL,
                 handle_pings: bool = True, loop: AbstractEventLoop = None):
        self._handle_pings = handle_pings
        self._incoming = asyncio.Queue(loop=loop)
        self._outgoing = asyncio.Queue(loop=loop)
        self._next_msg_id = 0xBEEF  # just for fun
        self._reply_map = {}
        self._room = room
        self._uri = uri_format.format(room)
        self._loop = loop
        self._sock = None
        self._sender = None
        self._receiver = None
        self._streams = weakref.WeakSet()

        self._started = asyncio.Event(loop=loop)
        self._connected = asyncio.Event(loop=loop)
        self._closed = asyncio.Event(loop=loop)

    def __repr__(self):
        fmt = "<euphoria.Client room='{0}' uri='{1}'>"
        return fmt.format(self._room, self._uri)

    @property
    def room(self) -> str:
        """The room this client may be connected to.

        :rtype: str"""
        return self._room

    @property
    def uri(self) -> str:
        """The URI this client will connect to.

        :rtype: str"""
        return self._uri

    @property
    def loop(self) -> AbstractEventLoop:
        """The asyncio event loop this client uses.

        :rtype: asyncio.AbstractEventLoop"""
        return self._loop

    @property
    def started(self) -> bool:
        """Returns whether this client has been started.

        :rtype: bool"""
        return self._started.is_set()

    @property
    def connected(self) -> bool:
        """Returns whether this client is connected to the server.

        :rtype: bool"""
        return self._connected.is_set()

    @property
    def closed(self) -> bool:
        """Returns whether this client is closed.

        :rtype: bool"""
        return self._closed.is_set()

    async def wait_until_started(self) -> None:
        """Wait until the client has been started.

        This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_."""
        await self._started.wait()

    async def wait_until_connected(self) -> None:
        """Pause execution of calling coroutine until client is connected.

        This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_."""
        assert not self.closed
        await self._connected.wait()

    async def wait_until_closed(self) -> None:
        """Paused execution of the calling coroutine until client has closed.

        This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_."""
        await self._closed.wait()

    def close(self) -> None:
        """Close the Client, never to be started again."""
        if self.closed:
            return

        logger.info("%s closing", self)

        self._connected.clear()
        self._closed.set()

        async def close_task():
            if self._sock and self._sock.open:
                await self._sock.close()

            if self._sender:
                self._sender.cancel()
                self._sender = None

            if self._receiver:
                self._receiver.cancel()
                self._receiver = None

            for v in self._reply_map.values():
                v.cancel()
            self._reply_map = {}

            for stream in self._streams:
                stream.close()
            self._streams = set()

            logger.debug("%s closed", self)

        asyncio.ensure_future(close_task(), loop=self._loop)

    async def stream(self) -> Stream:
        """Returns a Stream of messages to the Client.

        Waits until the Client is connected, then return a stream that gets a
        full view of all the received messages that aren't replies.

        This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_.

        :rtype: euphoria.Stream"""
        assert not self.closed
        await self.wait_until_connected()
        stream = Stream(loop=self._loop)
        self._streams.add(stream)
        return stream

    async def start(self) -> None:
        """Start the Client. This won't return until the Client is closed.

        This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_."""
        assert not self.started
        self._started.set()

        logger.info("%s connecting to %s", self, self._uri)
        self._sock = await websockets.connect(self._uri)

        self._sender = asyncio.ensure_future(self._send_loop(),
                                             loop=self._loop)
        self._receiver = asyncio.ensure_future(self._recv_loop(),
                                               loop=self._loop)
        self._connected.set()
        logger.info("%s connected", self)

        try:
            await asyncio.wait([self._sender, self._receiver],
                               return_when=asyncio.FIRST_COMPLETED,
                               loop=self._loop)
        finally:
            self.close()

    async def _send_loop(self) -> None:
        # This loop is started as a Task in Client.start(), it retrieves data from
        # the internal send queue and sends it out on the WebSocket.
        while self.connected:
            msg = await self._outgoing.get()
            logger.debug("%s sending message %s", self, msg)
            await self._sock.send(msg)

    async def _recv_loop(self) -> None:
        # This loop is started as a Task in Client.start(), it gets packets from
        # the WebSocket and routes them to the appropriate place.
        while self.connected:
            msg = await self._sock.recv()
            if msg is None:
                return
            logger.debug("%s got message %s", self, msg)
            packet = Packet(json.loads(msg))

            if packet.is_type(PingEvent) and self._handle_pings:
                self.send_ping_reply(packet.data.time)
                logger.debug("%s ping: %s", self, packet.data.time)
                continue

            if packet.id is not None:
                # If the message has an ID that means its a response to a
                # message we sent, so we put it into the corresponding future.
                fut = self._take_reply_future(packet.id)
                if fut:
                    fut.set_result(packet)
                continue

            to_delete = []
            for stream in self._streams:
                # Every stream should get a copy of this Packet.
                if stream.open:
                    stream._send(packet)
                else:
                    # Someone closed this stream so we can delete it at the end
                    # of the loop.
                    to_delete.append(stream)
            for stream in to_delete:
                self._streams.remove(stream)

    def _next_id_and_future(self) -> Tuple[str, Future]:
        # Generate a new ID to put into a message we are about to send, and
        # a corresponding future to receive the eventual reply from the server.
        id_ = str(self._next_msg_id)
        future = asyncio.Future()
        self._reply_map[id_] = future
        return id_, future

    def _take_reply_future(self, id_: str) -> Future:
        # If there is a future for this ID, then we retrieve it and remove it
        # from the map. (There will only be one response per ID.)
        if id_ in self._reply_map:
            future = self._reply_map[id_]
            del self._reply_map[id_]
            return future

    def _send_msg_with_reply_type(self, type_: str, data: dict) -> Future:
        # A small helper to send messages that will be replied to by the
        # server.
        id_, future = self._next_id_and_future()
        j = json.dumps({"type": type_, "id": id_, "data": data})
        self._outgoing.put_nowait(j)
        return future

    def _send_msg_no_reply(self, type_: str, data: dict) -> None:
        # A small helper to send a message that won't receive a reply from the
        # server.
        j = json.dumps({"type": type_, "data": data})
        self._outgoing.put_nowait(j)

    def send_nick(self, name: str) -> Future:
        """Sends a nick command to the server.

        :param str name: The new nick you want this Client to have
        :returns: A future that will contain a :py:class:`euphoria.NickReply`
        :rtype: asyncio.Future"""
        assert self.connected
        return self._send_msg_with_reply_type("nick", {"name": name})

    def send_ping_reply(self, time: int) -> None:
        """Sends a ping reply to the server.

        :param int time: The time you got passed in a PingEvent"""
        assert self.connected
        self._send_msg_no_reply("ping-reply", {"time": time})

    def send_auth(self, passcode: str) -> Future:
        """Sends an auth command to the server.

        :param str passcode: The password to the room the Client is connected to
        :returns: a future that will contain an :py:class:`euphoria.AuthReply`
        :rtype: asyncio.Future"""
        assert self.connected
        return self._send_msg_with_reply_type("auth",
                                              {"type": "passcode",
                                               "passcode": passcode})

    def send(self, content: str, parent: str = None) -> Future:
        """Sends a send command to the server.

        :param str content: The message you want this Client to say to the room
        :param str parent: The message ID you want to parent to
        :returns: A future that will contain a :py:class:`euphoria.SendReply`
        :rtype: asyncio.Future"""
        assert self.connected
        d = {"content": content}
        if parent:
            d["parent"] = parent
        return self._send_msg_with_reply_type("send", d)
