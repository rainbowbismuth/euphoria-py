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

from ..client import *
from ..stream import *
from ..data import *
from ..exceptions import *
import asyncio
import logging

logger = logging.getLogger(__name__)

# TODO: Take care of this detail: "the server may modify the requested nick."


class NickAndAuth:

    def __init__(self, client: Client, desired_nick: str):
        self._client = client
        self._desired_nick = desired_nick
        self._current_nick = None
        self._loop = client.loop
        self._passcode = None
        self._authorized = False
        self._started = asyncio.Event(loop=self._loop)
        self._closed = asyncio.Event(loop=self._loop)
        self._nick_cond = asyncio.Condition(loop=self._loop)
        self._nick_failure = asyncio.Event(loop=self._loop)
        self._auth_cond = asyncio.Condition(loop=self._loop)
        self._auth_failure = asyncio.Event(loop=self._loop)
        self._task = None
        self._nick_setter = None
        self._client_closer = asyncio.ensure_future(self._close_on_client(), loop=self._loop)

    async def _close_on_client(self):
        await self._client.wait_until_closed()
        self.close()

    @property
    def client(self) -> Client:
        return self._client

    @property
    def desired_nick(self) -> str:
        return self._desired_nick

    async def _nick_notifier(self):
        async with self._nick_cond:
            self._nick_cond.notify_all()

    def _try_new_nick(self):
        self._nick_failure.clear()
        if self.nick_is_desired():
            asyncio.ensure_future(self._nick_notifier(), loop=self._loop)
        else:
            if self._nick_setter:
                return
            self._nick_setter = asyncio.ensure_future(self._nick_setter_task(),
                                                      loop=self._loop)

    @desired_nick.setter
    def desired_nick(self, new_nick: str) -> None:
        if new_nick == self._desired_nick:
            return
        self._desired_nick = new_nick
        self._try_new_nick()

    @property
    def current_nick(self) -> str:
        return self._current_nick

    def _set_current_nick(self, new_nick: str) -> None:
        if new_nick == self._current_nick:
            return
        self._current_nick = new_nick
        self._try_new_nick()

    @property
    def passcode(self) -> str:
        return self._passcode

    @passcode.setter
    def passcode(self, new_code: str) -> None:
        self._passcode = new_code
        self._auth_failure.clear()

    @property
    def nick_failed(self) -> bool:
        return self._nick_failure.is_set()

    async def wait_until_nick_failure(self):
        await self._nick_failure.wait()

    @property
    def auth_failed(self) -> bool:
        return self._auth_failure.is_set()

    async def wait_until_auth_failure(self):
        await self._auth_failure.wait()

    @property
    def started(self) -> bool:
        return self._started.is_set()

    async def wait_until_started(self):
        await self._started.wait()

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def close(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
            self._closed.set()
        if self._nick_setter:
            self._nick_setter.cancel()
            self._nick_setter = None
        if self._client_closer:
            self._client_closer.cancel()
            self._client_closer = None

    async def wait_until_closed(self):
        await self._closed.wait()

    def nick_is_desired(self) -> bool:
        return self._desired_nick == self._current_nick

    async def wait_for_nick(self):
        async with self._nick_cond:
            await self._nick_cond.wait_for(self.nick_is_desired)

    def authorized(self) -> bool:
        return self._authorized

    async def _set_authorized(self, b: bool) -> None:
        if self._authorized == b:
            return
        self._authorized = b
        if self.authorized():
            async with self._auth_cond:
                self._auth_cond.notify_all()

    async def wait_for_auth(self):
        async with self._auth_cond:
            await self._auth_cond.wait_for(self.authorized)

    async def start(self):
        assert not self.started
        assert not self.closed

        self._started.set()
        stream = await self._client.stream()
        try:
            self._task = asyncio.ensure_future(self._main_loop(stream),
                                               loop=self._loop)
            await self._task
        finally:
            stream.close()
            self.close()

    async def _main_loop(self, stream: Stream):
        while True:
            try:
                packet = await stream.any()

                if packet.is_type(HelloEvent):
                    name = packet.data.session.name
                    self._set_current_nick(name)
                    await self._set_authorized(not packet.data.room_is_private)

                elif packet.is_type(BounceEvent):
                    if self.authorized():
                        self._set_authorized(False)
                        continue
                    if self.auth_failed:
                        continue
                    if not "passcode" in packet.data.auth_options:
                        logger.error("%s: no passcode method", self)
                        self._auth_failure.set()
                        continue
                    if not self._passcode:
                        logger.info(
                            "%s: passcode needed to auth, but not provided", self)
                        self._auth_failure.set()
                        continue
                    auth_reply = await self._client.send_auth(self._passcode)
                    if not auth_reply.data.success:
                        logger.info("%s: auth failure: %s",
                                    self, auth_reply.data.reason)
                        self._auth_failure.set()
                        continue
                    await self._set_authorized(True)

            except ErrorResponse:
                logger.debug("%s: error packet", self, exc_info=True)
                continue

    async def _nick_setter_task(self):
        await self.wait_for_auth()
        if self.nick_is_desired():
            return
        if self.nick_failed:
            return
        nick_reply = await self._client.send_nick(self._desired_nick)
        try:
            self._set_current_nick(nick_reply.data.to)
        except ErrorResponse:
            logger.debug("%s: error packet", self, exc_info=True)
            self._nick_failure.set()