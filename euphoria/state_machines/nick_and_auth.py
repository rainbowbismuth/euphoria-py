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

"""Nickname and authentication state machines."""

import asyncio
from asyncio import Future
import logging
from euphoria import Client

logger = logging.getLogger(__name__)


class NickAndAuth:
    def __init__(self, client: Client, desired_nick: str, passcode: str = ""):
        self._client = client
        self._stream = client.stream()
        self._desired_nick = desired_nick
        self._passcode = passcode
        self._loop = client.loop
        self._nick_future = None
        self._passcode_future = None
        self._partial_reset()
        asyncio.ensure_future(self._main_task(), loop=self._loop)

    def _partial_reset(self):
        self._current_nick = ""
        self._authorized = False
        if self._nick_future:
            self._nick_future.cancel()
            self._nick_future = None
        if self._passcode_future:
            self._passcode_future.cancel()
            self._passcode_future = None

    @property
    def current_nick(self) -> str:
        """Returns your current nickname, which may not be the one you desire.

        :rtype: str"""
        return self._current_nick

    @property
    def desired_nick(self) -> str:
        """Returns your desired nickname, which may not be your current one yet.

        :rtype: str"""
        return self._desired_nick

    @property
    def passcode(self) -> str:
        """Returns the passcode you will try on a BounceEvent.

        :rtype: str"""
        return self._passcode

    @property
    def authorized(self) -> bool:
        """Returns whether or not you're authorized.

        :rtype: bool"""
        return self._authorized

    def set_desired_nick(self, new_nick: str) -> Future:
        """Attempt to set your current_nick to new_nick.

        :param str new_nick: The new nickname you want to try.
        :returns: A future that will contain a string error message on failure, or None.
        :rtype: asyncio.Future"""
        self._desired_nick = new_nick
        if self._current_nick != self._desired_nick:
            self._nick_future = asyncio.ensure_future(self._nick_setter(), loop=self._loop)
        else:
            self._nick_future = asyncio.ensure_future(Future(loop=self._loop).set_result(None), loop=self._loop)
        return self._nick_future

    async def _nick_setter(self):
        logger.debug("%s: trying to set nick to %s", self, self._desired_nick)
        reply = await self._client.send_nick(self._desired_nick)
        if not reply.error:
            self._current_nick = reply.data.to
            self._desired_nick = reply.data.to
            logger.debug("%s: succeeded in setting nick to %s", self, self._current_nick)
            return None
        else:
            return reply.error

    def set_passcode(self, new_passcode: str) -> Future:
        """Sets your passcode to new_passcode and attempts to authenticate if not already.

        :param str new_passcode: The new passcode you want to try.
        :returns: A future that will contain a string error message on failure, or None.
        :rtype: asyncio.Future"""
        self._passcode = new_passcode
        if not self._authorized:
            self._passcode_future = asyncio.ensure_future(self._passcode_setter(), loop=self._loop)
        else:
            self._passcode_future = asyncio.ensure_future(Future(loop=self._loop).set_result(None), loop=self._loop)
        return self._passcode_future

    async def _passcode_setter(self):
        logger.debug("%s: trying to set passcode to %s", self, self._passcode)
        reply = await self._client.send_auth(self._passcode)
        if not reply.error and reply.data.success:
            self._authorized = True
            self.set_desired_nick(self._desired_nick)
            logger.debug("%s: successfully authenticated with passcode", self)
            return None
        else:
            return reply.error

    async def _main_task(self):
        while True:
            packet = await self._stream.any()

            msg = packet.hello_event
            if msg:
                logger.debug("%s: got HelloEvent", self)
                self._partial_reset()
                self._current_nick = msg.session.name
                self._authorized = not msg.room_is_private
                if self._authorized:
                    self.set_desired_nick(self.desired_nick)
                continue

            msg = packet.bounce_event
            if msg:
                logger.debug("%s: got BounceEvent", self)
                self._partial_reset()
                self._current_nick = ""
                self._authorized = False
                if "passcode" in msg.auth_options:
                    self.set_passcode(self.passcode)
