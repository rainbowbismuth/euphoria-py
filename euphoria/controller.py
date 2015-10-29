# TODO: add docstring

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
from euphoria import PingEvent, HelloEvent, NickReply, BounceEvent

#
# This file is very.... experimental. I really have no idea how this is going
# to take form.
#


class PingController:
    # TODO: add docstring

    def __init__(self, bot):
        self._bot = bot
        self._loop = bot.loop

    @property
    def bot(self):
        # TODO: add docstring
        return self._bot

    async def start(self):
        # TODO: add docstring
        stream = await self._bot.stream()
        while True:
            ping = await stream.skip_until(PingEvent)
            await self._bot.send_ping_reply(ping.data.time)


class NickAndAuthController:
    # TODO: add docstring

    def __init__(self, bot, desired_nick, passcode=None):
        self._bot = bot
        self._loop = bot.loop
        self._desired_nick = desired_nick
        self._current_nick = None
        self._passcode = passcode
        self._authenticated = False

    @property
    def bot(self):
        # TODO: add docstring
        return self._bot

    @property
    def desired_nick(self):
        # TODO: add docstring
        return self._desired_nick

    @property
    def current_nick(self):
        # TODO: add docstring
        return self._current_nick

    @property
    def authenticated(self):
        # TODO: add docstring
        return self._authenticated

    async def start(self):
        stream = await self._bot.stream()
        while True:
            packet = await stream.any()
            if packet.is_type(HelloEvent):
                self._current_nick = packet.data.session.name
                if self._current_nick != self._desired_nick:
                    await self._try_send_nick()

            elif packet.is_type(BounceEvent):
                assert self._passcode
                auth_reply_fut = await self._bot.send_auth(self._passcode)
                auth_reply = await auth_reply_fut
                if not auth_reply.error and \
                        self._current_nick != self._desired_nick:
                    await self._try_send_nick()

    async def _try_send_nick(self):
        nick_reply_fut = await self._bot.send_nick(self._desired_nick)
        nick_reply = await nick_reply_fut
        if nick_reply.error:
            return
        self._current_nick = nick_reply.data.to
