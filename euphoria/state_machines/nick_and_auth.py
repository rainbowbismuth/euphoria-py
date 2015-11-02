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

import logging
from asyncio import AbstractEventLoop
from typing import Optional

from euphoria import Client, Packet
from tiny_agent import Agent

logger = logging.getLogger(__name__)


__all__ = ['NickAndAuth']

class NickAndAuth(Agent):
    def __init__(self, client: Client, desired_nick: str, passcode: str = "", loop: AbstractEventLoop = None):
        super(NickAndAuth, self).__init__(loop=loop)
        self._client = client
        self._client.add_listener(self)

        self._desired_nick = desired_nick
        self._current_nick = ""
        self._passcode = passcode
        self._authorized = False

    @property
    def desired_nick(self) -> str:
        return self._desired_nick

    @property
    def current_nick(self) -> str:
        return self._current_nick

    @property
    def passcode(self) -> str:
        return self._passcode

    @property
    def authorized(self) -> bool:
        return self._authorized

    @Agent.call
    async def set_desired_nick(self, new_nick: str) -> Optional[str]:
        self._desired_nick = new_nick
        packet = await self._client.send_nick(new_nick)
        if packet.error:
            return packet.error
        else:
            nick_reply = packet.nick_reply
            self._current_nick = nick_reply.to
            self._desired_nick = nick_reply.to
            return None

    @Agent.call
    async def set_passcode(self, new_passcode: str) -> Optional[str]:
        self._passcode = new_passcode
        packet = await self._client.send_auth(new_passcode)
        if packet.error:
            return packet.error
        else:
            auth_reply = packet.auth_reply
            assert auth_reply.success
            self._authorized = True
            self.set_desired_nick(self._desired_nick)
            return None

    @Agent.send
    async def on_packet(self, packet: Packet):
        hello_event = packet.hello_event
        if hello_event:
            self._current_nick = hello_event.session.name
            self._authorized = not hello_event.room_is_private
            if self._authorized:
                self.set_desired_nick(self._desired_nick)
            return

        bounce_event = packet.bounce_event
        if bounce_event:
            self._authorized = False
            self.set_passcode(self._passcode)
