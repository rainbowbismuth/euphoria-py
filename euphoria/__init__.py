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
import websockets
import json
import inspect
import logging
from .data import *

logger = logging.getLogger(__name__)

EUPHORIA_URL = "wss://euphoria.io:443/room/{0}/ws"


class Client:
    # TODO: Add docstring

    def __init__(self, room, uri_format=EUPHORIA_URL, loop=None):
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
        self._streams = set()

        self._connected = asyncio.Event(loop=loop)
        self._closed = asyncio.Event(loop=loop)

    @property
    def room(self):
        """The room this client may be connected to."""
        return self._room

    @property
    def uri(self):
        """The URI this client will connect to."""
        return self._uri

    @property
    def loop(self):
        """The asyncio event loop this client uses."""
        return self._loop

    @property
    def connected(self):
        """Returns whether this client is connected to the server."""
        return self._connected.is_set()

    @property
    def closed(self):
        """Returns whether this client is closed."""
        return self._closed.is_set()

    async def wait_until_connected(self):
        """Pause execution of calling coroutine until client is connected."""
        assert not self.closed
        await self._connected.wait()

    async def wait_until_closed(self):
        """Paused execution of the calling coroutine until client has closed."""
        await self._closed.wait()

    async def close(self):
        """Close the Client, never to be started again."""
        if self.closed:
            return

        logger.info("%s closing", self)

        self._connected.clear()
        self._closed.set()

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

    async def stream(self):
        """Wait until the Client is connected, then return a stream that gets a
         full view of all the received messages that aren't replies."""
        assert not self.closed
        await self.wait_until_connected()
        stream = Stream(loop=self._loop)
        self._streams.add(stream)
        return stream

    async def start(self):
        """Start the Client. This won't return until the Client is closed."""
        assert not self.closed

        logger.info("%s connecting to %s", self, self._uri)
        self._sock = await websockets.connect(self._uri)

        self._sender = asyncio.ensure_future(self._send_loop(),
                                             loop=self._loop)
        self._receiver = asyncio.ensure_future(self._recv_loop(),
                                               loop=self._loop)
        self._connected.set()
        logger.info("%s connected", self)

        await self._wait_then_close()

    async def _wait_then_close(self):
        try:
            await asyncio.wait([self._sender, self._receiver],
                               return_when=asyncio.FIRST_COMPLETED,
                               loop=self._loop)
        finally:
            await self.close()

    async def _send_loop(self):
        # This loop is started as a Task in Client.start(), it retrieves data from
        # the internal send queue and sends it out on the WebSocket.
        while self.connected:
            msg = await self._outgoing.get()
            logger.debug("%s sending message %s", self, msg)
            await self._sock.send(msg)

    async def _recv_loop(self):
        # This loop is started as a Task in Client.start(), it gets packets from
        # the WebSocket and routes them to the appropriate place.
        while self.connected:
            msg = await self._sock.recv()
            if msg is None:
                return
            logger.debug("%s got message %s", self, msg)
            packet = Packet(json.loads(msg))
            if packet.id is not None:
                # If the message has an ID that means its a response to a
                # message we sent, so we put it into the corresponding future.
                fut = self._take_reply_future(packet.id)
                if fut:
                    fut.set_result(packet)
                continue

            assert packet.data is not None
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

    def _next_id_and_future(self):
        # Generate a new ID to put into a message we are about to send, and
        # a corresponding future to recieve the eventual reply from the server.
        id_ = str(self._next_msg_id)
        future = asyncio.Future()
        self._reply_map[id_] = future
        return (id_, future)

    def _take_reply_future(self, id_):
        # If there is a future for this ID, then we retrieve it and remove it
        # from the map. (There will only be one response per ID.)
        if id_ in self._reply_map:
            future = self._reply_map[id_]
            del self._reply_map[id_]
            return future

    async def _send_msg_with_reply_type(self, type_, data):
        # A small helper to send messages that will be replied to by the
        # server.
        id_, future = self._next_id_and_future()
        j = json.dumps({"type": type_, "id": id_, "data": data})
        await self._outgoing.put(j)
        return future

    async def _send_msg_no_reply(self, type_, data):
        # A small helper to send a message that won't receive a reply from the
        # server.
        j = json.dumps({"type": type_, "data": data})
        await self._outgoing.put(j)

    async def send_nick(self, name):
        """Sends a nick command to the server. Returns a future that will
         contain a nick-reply."""
        assert self.connected
        return await self._send_msg_with_reply_type("nick", {"name": name})

    async def send_ping_reply(self, time):
        """Sends a ping reply to the server."""
        assert self.connected
        await self._send_msg_no_reply("ping-reply", {"time": time})

    async def send_auth(self, passcode):
        """Sends an auth command to the server. Returns a future that will
         contain an auth-reply."""
        assert self.connected
        return await self._send_msg_with_reply_type("auth",
                                                    {"type": "passcode",
                                                     "passcode": passcode})

    async def send(self, content, parent=None):
        """Sends a send command to the server. Returns a future that will
         contain a send-reply."""
        assert self.connected
        return await self._send_msg_with_reply_type("send",
                                                    {"content": content})


class Stream:
    # TODO: Add docstring

    def __init__(self, loop=None):
        self._loop = loop
        self._client_open = True
        self._queue = asyncio.Queue(loop=loop)
        self._waiting_on = None

    def _send(self, packet):
        # This is used by Client's receive loop to put an item into the Stream.
        self._queue.put_nowait(packet)

    def close(self):
        """Closes this stream. Will not receive any more messages from the Client."""
        self._client_open = False
        if self._waiting_on:
            # If there's somebody waiting inside a Stream.any() we have to
            # cancel them because no more messages are coming.
            self._waiting_on.cancel()

    @property
    def loop(self):
        """The asyncio event loop this Stream uses."""
        return self._loop

    @property
    def open(self):
        """Returns whether this stream can receive messages from the Client."""
        return self._client_open

    async def any(self):
        """Returns the next message from the Client."""
        # Only one coroutine should be using a stream, so if self._waiting_on
        # isn't None, then clearly more then one coroutine is using it.
        assert self._waiting_on is None
        self._waiting_on = asyncio.ensure_future(
            self._queue.get(), loop=self._loop)
        try:
            result = await self._waiting_on
            return result
        finally:
            self._waiting_on = None

    async def skip_until(self, condition):
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

    async def select(self, condition):
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
