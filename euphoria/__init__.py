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

logger = logging.getLogger(__name__)


class Packet:

    def __init__(self, j):
        self.id = j.get('id', None)
        self.type = j['type']
        if j.get('data', None):
            self._data = DATA_TYPES[self.type](j['data'])
        else:
            self._data = None
        self.error = j.get('error', None)
        self.throttled = j.get('throttled', False)
        self.throttled_reason = j.get('throttled_reason', None)

    def is_type(self, type_):
        return self.data and isinstance(self.data, type_)

    @property
    def data(self):
        if self.error:
            raise Exception(self.error)
        if self.throttled:
            raise Exception(self.throttled_reason)
        return self._data


class HelloEvent:

    def __init__(self, j):
        self.id = j['id']
        self.account = j.get('account', None)
        self.session = SessionView(j['session'])
        self.account_has_access = j.get('account_has_access', True)
        self.room_is_private = j.get('room_is_private')
        self.version = j.get('version')


class PingEvent:

    def __init__(self, j):
        self.time = j['time']
        self.next = j['next']


class BounceEvent:

    def __init__(self, j):
        self.reason = j['reason']


class AuthReply:

    def __init__(self, j):
        self.success = j['success']


class SnapshotEvent:

    def __init__(self, j):
        self.identity = j['identity']
        self.session_id = j['session_id']
        self.version = j['version']
        self.listing = [SessionView(sub_j) for sub_j in j['listing']]
        self.log = [Message(sub_j) for sub_j in j['log']]


class NickEvent:

    def __init__(self, j):
        self.session_id = j['session_id']
        self.id = j['id']
        self.from_ = j['from']
        self.to = j['to']


class NickReply:

    def __init__(self, j):
        self.session_id = j['session_id']
        self.id = j['id']
        self.from_ = j['from']
        self.to = j['to']


class Message:

    def __init__(self, j):
        self.id = j['id']
        self.parent = j.get('parent', None)
        self.previous_edit_id = j.get('previous_edit_id', None)
        self.time = j['time']
        self.sender = SessionView(j['sender'])
        self.content = j['content']
        self.encryption_key_id = j.get('encryption_key_id', None)
        self.edited = j.get('edited', None)
        self.deleted = j.get('deleted', None)
        self.truncated = j.get('truncated', False)


class SendEvent:

    def __init__(self, j):
        self.id = j['id']
        self.parent = j.get('parent', None)
        self.previous_edit_id = j.get('previous_edit_id', None)
        self.time = j['time']
        self.sender = SessionView(j['sender'])
        self.content = j['content']
        self.encryption_key_id = j.get('encryption_key_id', None)
        self.edited = j.get('edited', None)
        self.deleted = j.get('deleted', None)
        self.truncated = j.get('truncated', False)


class SendReply:

    def __init__(self, j):
        self.id = j['id']
        self.parent = j.get('parent', None)
        self.previous_edit_id = j.get('previous_edit_id', None)
        self.time = j['time']
        self.sender = SessionView(j['sender'])
        self.content = j['content']
        self.encryption_key_id = j.get('encryption_key_id', None)
        self.edited = j.get('edited', None)
        self.deleted = j.get('deleted', None)
        self.truncated = j.get('truncated', False)


class SessionView:

    def __init__(self, j):
        self.id = j['id']
        self.name = j['name']
        self.server_id = j['server_id']
        self.server_era = j['server_era']
        self.session_id = j['session_id']
        self.is_staff = j.get('is_staff', False)
        self.is_manager = j.get('is_manager', False)


class JoinEvent:

    def __init__(self, j):
        self.id = j['id']
        self.name = j['name']
        self.server_id = j['server_id']
        self.server_era = j['server_era']
        self.session_id = j['session_id']
        self.is_staff = j.get('is_staff', False)
        self.is_manager = j.get('is_manager', False)

DATA_TYPES = {'hello-event': HelloEvent,
              'snapshot-event': SnapshotEvent,
              'ping-event': PingEvent,
              'bounce-event': BounceEvent,
              'auth-reply': AuthReply,
              'nick-event': NickEvent,
              'nick-reply': NickReply,
              'send-event': SendEvent,
              'send-reply': SendReply,
              'join-event': JoinEvent}


class EuphoriaBot:

    def __init__(self, room, uri_format="wss://euphoria.io:443/room/{0}/ws", loop=None):
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
        return self._room

    @property
    def uri(self):
        return self._uri

    @property
    def loop(self):
        return self._loop

    @property
    def connected(self):
        return self._connected.is_set()

    @property
    def closed(self):
        return self._closed.is_set()

    async def wait_until_connected(self):
        await self._connected.wait()

    async def wait_until_closed(self):
        await self._closed.wait()

    async def close(self):
        if self.closed:
            return

        logger.info("{0} closing".format(self))

        self._connected.clear()
        self._closed.set()

        if self._sock and self._sock.open:
            await self._sock.close()

        if self._sender:
            self._sender.cancel()

        if self._receiver:
            self._receiver.cancel()

        for v in self._reply_map.values():
            v.cancel()
        self._reply_map = {}

        for stream in self._streams:
            stream.close()
        self._streams = set()

        logger.debug("{0} closed".format(self))

    async def stream(self):
        await self.wait_until_connected()
        stream = EuphoriaStream(loop=self._loop)
        self._streams.add(stream)
        return stream

    async def start(self):
        assert self._sock == None
        assert self._sender == None
        assert self._receiver == None

        logger.info("{0} connecting to {1}".format(self, self._uri))
        self._sock = await websockets.connect(self._uri)

        self._sender = asyncio.ensure_future(self._send_loop(),
                                             loop=self._loop)
        self._receiver = asyncio.ensure_future(self._recv_loop(),
                                               loop=self._loop)
        self._connected.set()
        logger.info("{0} connected".format(self))

        await self._wait_then_close()

    async def _wait_then_close(self):
        try:
            await asyncio.wait([self._sender, self._receiver],
                               return_when=asyncio.FIRST_COMPLETED, loop=self._loop)
        finally:
            await self.close()

    async def _send_loop(self):
        while self.connected:
            msg = await self._outgoing.get()
            logger.debug("{0} sending message {1}".format(self, msg))
            await self._sock.send(msg)

    async def _recv_loop(self):
        while self.connected:
            msg = await self._sock.recv()
            if msg == None:
                return
            logger.debug("{0} got message {1}".format(self, msg))
            packet = Packet(json.loads(msg))
            if packet.id != None:
                fut = self._take_reply_future(packet.id)
                if fut:
                    fut.set_result(packet)
                continue

            assert packet.data is not None
            to_delete = []
            for stream in self._streams:
                if stream.open:
                    stream._send(packet)
                else:
                    to_delete.append(stream)
            for stream in to_delete:
                self._streams.remove(stream)

    def _next_id_and_future(self):
        id_ = str(self._next_msg_id)
        future = asyncio.Future()
        self._reply_map[id_] = future
        return (id_, future)

    def _take_reply_future(self, id_):
        if id_ in self._reply_map:
            future = self._reply_map[id_]
            del self._reply_map[id_]
            return future

    async def _send_msg_with_reply_type(self, type_, data):
        id_, future = self._next_id_and_future()
        j = json.dumps({"type": type_, "id": id_, "data": data})
        await self._outgoing.put(j)
        return future

    async def _send_msg_no_reply(self, type_, data):
        j = json.dumps({"type": type_, "data": data})
        await self._outgoing.put(j)

    async def send_nick(self, name):
        return await self._send_msg_with_reply_type("nick", {"name": name})

    async def send_ping_reply(self, time):
        await self._send_msg_no_reply("ping-reply", {"time": time})

    async def send_auth(self, passcode):
        return await self._send_msg_with_reply_type("auth",
                                                    {"type": "passcode", "passcode": passcode})

    async def send(self, content, parent=None):
        return await self._send_msg_with_reply_type("send", {"content": content})


class EuphoriaStream:

    def __init__(self, loop=None):
        self._loop = loop
        self._bot_open = True
        self._queue = asyncio.Queue(loop=loop)
        self._waiting_on = None

    def _send(self, packet):
        self._queue.put_nowait(packet)

    def close(self):
        self._bot_open = False
        if self._waiting_on:
            self._waiting_on.cancel()

    @property
    def open(self):
        return self._bot_open

    async def any(self):
        assert self._waiting_on is None
        self._waiting_on = asyncio.ensure_future(self._queue.get())
        result = await self._waiting_on
        self._waiting_on = None
        return result

    async def skip_until(self, condition):
        if inspect.isclass(condition):
            kls = condition
            condition = lambda p: p.data and isinstance(p.data, kls)

        while True:
            packet = await self.any()
            if not condition(packet):
                continue
            return packet

    async def select(self, condition):
        if inspect.isclass(condition):
            kls = condition
            condition = lambda p: p.data and isinstance(p.data, kls)

        while True:
            packet = await self.any()
            if not condition(packet):
                self._queue.put_nowait(packet)
                continue

            return packet
