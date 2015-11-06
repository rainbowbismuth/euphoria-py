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
from asyncio import Future, AbstractEventLoop
from typing import Tuple

import websockets

import tiny_agent
from euphoria import Packet, PingEvent
from tiny_agent import Agent

__all__ = ['Client']

logger = logging.getLogger(__name__)

EUPHORIA_URL = "wss://euphoria.io:443/room/{0}/ws"


class Client(Agent):
    @tiny_agent.init
    def __init__(self, room: str, uri_format: str = EUPHORIA_URL,
                 handle_pings: bool = True, loop: AbstractEventLoop = None):
        super(Client, self).__init__(loop=loop)
        self._next_msg_id = 0xBEEF  # just for fun
        self._reply_map = {}
        self._room = room
        self._uri = uri_format.format(room)
        self._handle_pings = handle_pings
        self._sock = None
        self._receiver = None
        self._listeners = set()

    def __repr__(self):
        fmt = "<euphoria.Client room='{0}' uri='{1}'>"
        return fmt.format(self._room, self._uri)

    @property
    def room(self) -> str:
        return self._room

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def handle_pings(self) -> bool:
        return self._handle_pings

    @property
    def connected(self) -> bool:
        return self._sock and self._sock.open

    @tiny_agent.send
    async def connect(self):
        assert self.alive, "we better be alive to be connected"
        assert not self.connected, "make sure we don't get connected twice ever"
        self._sock = await websockets.connect(self._uri)

        async def receive_loop():
            try:
                while self.alive:
                    msg = await self._sock.recv()
                    if msg is None:
                        return
                    logger.debug("%s got message %s", self, msg)
                    packet = Packet(json.loads(msg))

                    if packet.is_type(PingEvent) and self._handle_pings:
                        self.send_ping_reply(packet.data.time)

                    if packet.id is not None:
                        # If the message has an ID that means its a response to a
                        # message we sent, so we put it into the corresponding future.
                        fut = self._take_reply_future(packet.id)
                        if fut:
                            fut.set_result(packet)

                    to_remove = []
                    for listener in self._listeners:
                        if listener.alive:
                            listener.on_packet(packet)
                        else:
                            to_remove.append(listener)
                    for listener in to_remove:
                        self._listeners.remove(listener)
            finally:
                await self._sock.close()

        self._receiver = self.spawn_linked_task(receive_loop(), unlink_on_success=False)

    def add_listener(self, listener: Agent):
        self._listeners.add(listener)

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

    @tiny_agent.send
    async def _send_packet(self, packet: str):
        if self.connected:
            logger.debug("%s sending message %s", self, packet)
            await self._sock.send(packet)

    def _send_msg_with_reply_type(self, type_: str, data: dict) -> Future:
        # A small helper to send messages that will be replied to by the
        # server.
        id_, future = self._next_id_and_future()
        j = json.dumps({"type": type_, "id": id_, "data": data})
        self._send_packet(j)
        return future

    def _send_msg_no_reply(self, type_: str, data: dict) -> None:
        # A small helper to send a message that won't receive a reply from the
        # server.
        j = json.dumps({"type": type_, "data": data})
        self._send_packet(j)

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

        :returns: A future that would contain a :py:class:`euphoria.GetMessageReply`
        :rtype: asyncio.Future"""
        return self._send_msg_with_reply_type("get-message", {"id": id_})
