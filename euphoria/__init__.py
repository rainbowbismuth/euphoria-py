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

"""Euphoria client and bot library, for Python 3.5"""

# noinspection PyUnresolvedReferences
from .exceptions import EuphoriaException, ErrorResponse
# noinspection PyUnresolvedReferences
from .data import Packet, SessionView, Message, SendEvent, SnapshotEvent, JoinEvent, HelloEvent, BounceEvent, PingEvent, \
    NetworkEvent, NickEvent, SendReply, NickReply
# noinspection PyUnresolvedReferences
from .stream import Stream
# noinspection PyUnresolvedReferences
from .client import Client
# noinspection PyUnresolvedReferences
from .bot import Bot, BotConfig

__all__ = ['exceptions', 'data', 'stream', 'client', 'bot']
