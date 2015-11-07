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
from asyncio import Future, AbstractEventLoop, Queue, Task
from typing import Tuple

import websockets

import euphoria
from euphoria import Packet, PingEvent

__all__ = ['SendQueue', 'connect']

logger = logging.getLogger(__name__)

EUPHORIA_URL = "wss://euphoria.io:443/room/{0}/ws"


class SendQueue:
    def __init__(self, loop: AbstractEventLoop = None):
        self._loop = loop
        self._queue = Queue(loop=loop)
        self._next_msg_id = 0xBEEF  # just for fun

    @property
    def underlying_queue(self) -> Queue:
        """Returns the underlying asyncio queue.

        :rtype: asyncio.Queue"""
        return self._queue

    def _next_id_and_future(self) -> Tuple[str, Future]:
        id_ = str(self._next_msg_id)
        future = asyncio.Future(loop=self._loop)
        self._next_msg_id += 1
        return id_, future

    def _send_msg_with_reply_type(self, type_: str, data: dict) -> Future:
        id_, future = self._next_id_and_future()
        packet = {"type": type_, "id": id_, "data": data}
        self._queue.put_nowait((future, packet))
        return future

    def _send_msg_no_reply(self, type_: str, data: dict) -> None:
        packet = {"type": type_, "data": data}
        self._queue.put_nowait((None, packet))

    def send_nick(self, name: str) -> Future:
        """Sends a nick command to the server.

        :param str name: The new nick you want this Client to have
        :returns: A future that will contain a :py:class:`euphoria.NickReply`
        :rtype: asyncio.Future"""
        return self._send_msg_with_reply_type("nick", {"name": name})

    def send_ping_reply(self, time: int) -> None:
        """Sends a ping reply to the server.

        :param int time: The time you got passed in a PingEvent"""
        self._send_msg_no_reply("ping-reply", {"time": time})

    def send_auth(self, passcode: str) -> Future:
        """Sends an auth command to the server.

        :param str passcode: The password to the room the Client is connected to
        :returns: a future that will contain an :py:class:`euphoria.AuthReply`
        :rtype: asyncio.Future"""
        return self._send_msg_with_reply_type("auth",
                                              {"type": "passcode",
                                               "passcode": passcode})

    def send_content(self, content: str, parent: str = None) -> Future:
        """Sends a send command to the server.

        :param str content: The message you want this Client to say to the room
        :param str parent: The message ID you want to parent to
        :returns: A future that will contain a :py:class:`euphoria.SendReply`
        :rtype: asyncio.Future"""
        d = {"content": content}
        if parent:
            d["parent"] = parent
        return self._send_msg_with_reply_type("send", d)

    def send_log_command(self, before: str, n: int = 10) -> Future:
        return self._send_msg_with_reply_type("log", {"before": before, "n": n})

    def send_get_message(self, id_: str) -> Future:
        """Sends a get-message command to the server.

        :param str id_: The ID of the message you wish to retrieve
        :returns: A future that would contain a :py:class:`euphoria.GetMessageReply`
        :rtype: asyncio.Future"""
        return self._send_msg_with_reply_type("get-message", {"id": id_})


class Client:
    def __init__(self, uri: str, handle_pings: bool, loop: AbstractEventLoop = None):
        self._loop = loop
        self._uri = uri
        self._reply_map = {}
        self._handle_pings = handle_pings
        self._sock = None
        self._send_queue = SendQueue(loop=loop)
        self._receive_queue = Queue(loop=loop)

    @property
    def send_queue(self) -> SendQueue:
        return self._send_queue

    @property
    def receive_queue(self) -> Queue:
        return self._receive_queue

    async def connect(self) -> None:
        self._sock = await websockets.connect(self._uri)
        await euphoria.links([self._receive_loop(), self._send_loop()], loop=self._loop)
        return

    def _take_reply_future(self, id_: str) -> Future:
        # If there is a future for this ID, then we retrieve it and remove it
        # from the map. (There will only be one response per ID.)
        if id_ in self._reply_map:
            future = self._reply_map[id_]
            del self._reply_map[id_]
            return future

    async def _receive_loop(self):
        while True:
            msg = await self._sock.recv()
            if msg is None:
                raise Exception("client disconnected")

            packet = Packet(json.loads(msg))

            if packet.is_type(PingEvent) and self._handle_pings:
                self._send_queue.send_ping_reply(packet.data.time)

            if packet.id:
                # If the message has an ID that means its a response to a
                # message we sent, so we put it into the corresponding future.
                fut = self._take_reply_future(packet.id)
                if fut:
                    fut.set_result(packet)

            self._receive_queue.put_nowait(packet)

    async def _send_loop(self):
        while True:
            (fut, packet) = await self._send_queue.underlying_queue.get()
            if fut:
                self._reply_map[packet["id"]] = fut
            msg = json.dumps(packet)
            await self._sock.send(msg)


def connect(room: str, uri_format: str = EUPHORIA_URL, handle_pings: bool = True, loop: AbstractEventLoop = None) -> \
        Tuple[Task, SendQueue, Queue]:
    uri = uri_format.format(room)
    client = Client(uri, handle_pings=handle_pings, loop=loop)
    send = client.send_queue
    receive = client.receive_queue
    connect_task = asyncio.ensure_future(client.connect(), loop=loop)
    return connect_task, send, receive
