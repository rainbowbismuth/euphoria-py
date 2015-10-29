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

from .exceptions import *

class Packet:
    # TODO: Add docstring

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
        """Returns whether or this packet contains data of the given type."""
        return self.data and isinstance(self.data, type_)

    @property
    def data(self):
        """Returns the data part of the Packet.

        Throws an exception if Packet contains an error or throttle message."""
        if self.error:
            raise ErrorResponse(self.error)
        if self.throttled:
            raise ThrottledResponse(self.throttled_reason)
        return self._data


class HelloEvent:
    # TODO: Add docstring

    def __init__(self, j):
        self.id = j['id']
        self.account = j.get('account', None)
        self.session = SessionView(j['session'])
        self.account_has_access = j.get('account_has_access', True)
        self.room_is_private = j.get('room_is_private')
        self.version = j.get('version')


class PingEvent:
    # TODO: Add docstring

    def __init__(self, j):
        self.time = j['time']
        self.next = j['next']


class BounceEvent:
    # TODO: Add docstring

    def __init__(self, j):
        self.reason = j['reason']


class AuthReply:
    # TODO: Add docstring

    def __init__(self, j):
        self.success = j['success']


class SnapshotEvent:
    # TODO: Add docstring

    def __init__(self, j):
        self.identity = j['identity']
        self.session_id = j['session_id']
        self.version = j['version']
        self.listing = [SessionView(sub_j) for sub_j in j['listing']]
        self.log = [Message(sub_j) for sub_j in j['log']]


class NickEvent:
    # TODO: Add docstring

    def __init__(self, j):
        self.session_id = j['session_id']
        self.id = j['id']
        self.from_ = j['from']
        self.to = j['to']


class NickReply:
    # TODO: Add docstring

    def __init__(self, j):
        self.session_id = j['session_id']
        self.id = j['id']
        self.from_ = j['from']
        self.to = j['to']


class Message:
    # TODO: Add docstring

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
    # TODO: Add docstring

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
    # TODO: Add docstring

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
    # TODO: Add docstring

    def __init__(self, j):
        self.id = j['id']
        self.name = j['name']
        self.server_id = j['server_id']
        self.server_era = j['server_era']
        self.session_id = j['session_id']
        self.is_staff = j.get('is_staff', False)
        self.is_manager = j.get('is_manager', False)


class JoinEvent:
    # TODO: Add docstring

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
