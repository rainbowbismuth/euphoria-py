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

"""Contains all the different types you may receive from the euphoria server"""

from typing import Any, List
from .exceptions import *


class Packet:
    """A message recieved from Euphoria"""

    def __init__(self, j: dict):
        self._id = j.get('id', None)
        self._type = j['type']
        if j.get('data', None):
            self._data = DATA_TYPES[self.type](j['data'])
        else:
            self._data = None
        self._error = j.get('error', None)
        self._throttled = j.get('throttled', False)
        self._throttled_reason = j.get('throttled_reason', None)

    def is_type(self, type_: str) -> bool:
        """Returns whether or not this packet contains data of the given type.

        :rtype: bool"""
        return isinstance(self._data, type_)

    @property
    def id(self) -> str:
        """Client-generated ID that associates replies with commands. Will be
        None if this Packet isn't in response to a command.

        :rtype: str"""
        return self._id

    @property
    def type(self) -> str:
        """A string name of the type of data associated with this Packet.

        :rtype: str"""
        return self._type

    @property
    def data(self) -> Any:
        """Returns the data part of the Packet.

        :raises euphoria.ErrorResponse: if this Packet contains an error."""
        if self.error:
            raise ErrorResponse(self.error)
        return self._data

    @property
    def error(self) -> str:
        """An error message if a command fails. None otherwise.

        :rtype: str"""
        return self._error

    @property
    def throttled(self) -> bool:
        """This appears true in replies to warn the client that it may be
        flooding commands.

        :rtype: bool"""
        return self._throttled

    @property
    def throttled_reason(self) -> str:
        """If Packet.throttled is true, then this is a string describing why.

        :rtype: str"""
        return self._throttled_reason


class SessionViewBased:

    def __init__(self, j: dict):
        self._id = j['id']
        self._name = j['name']
        self._server_id = j['server_id']
        self._server_era = j['server_era']
        self._session_id = j['session_id']
        self._is_staff = j.get('is_staff', False)
        self._is_manager = j.get('is_manager', False)

    @property
    def id(self) -> str:
        """The id of an agent or account.

        :rtype: str"""
        return self._id

    @property
    def name(self) -> str:
        """The name-in-use at the time this view was captured.

        :rtype: str"""
        return self._name

    @property
    def server_id(self) -> str:
        """The id of the server that captured this view.

        :rtype: str"""
        return self._server_id

    @property
    def server_era(self) -> str:
        """The era of the server that captured this view.

        :rtype: str"""
        return self._server_era

    @property
    def session_id(self) -> str:
        """ID of the session, unique across all sessions globally.

        :rtype: str"""
        return self._session_id

    @property
    def is_staff(self) -> bool:
        """If true, this session belongs to a member of staff.

        :rtype: bool"""
        return self._is_staff

    @property
    def is_manager(self) -> bool:
        """If true, this session belongs to a manager of the room.

        :rtype: bool"""
        return self._is_manager


class SessionView(SessionViewBased):
    """A SessionView describes a session and its identity."""


class MessageBased:

    def __init__(self, j: dict):
        self._id = j['id']
        self._edit_id = j.get('edit_id', None)
        self._parent = j.get('parent', None)
        self._previous_edit_id = j.get('previous_edit_id', None)
        self._time = j['time']
        self._sender = SessionView(j['sender'])
        self._content = j['content']
        self._encryption_key_id = j.get('encryption_key_id', None)
        self._edited = j.get('edited', None)
        self._deleted = j.get('deleted', None)
        self._truncated = j.get('truncated', False)

    @property
    def id(self) -> str:
        """The id of the message (unique within a room).

        :rtype: str"""
        return self._id

    @property
    def edit_id(self) -> str:
        """The ID of the edit. None if this isn't an EditMessageEvent.

        :rtype: str"""

    @property
    def parent(self) -> str:
        """The id of the message's parent, or None if top-level.

        :rtype: str"""
        return self._parent

    @property
    def previous_edit_id(self) -> str:
        """The edit id of the most recent edit of this message, or None if it's
        never been edited.

        :rtype: str"""
        return self._previous_edit_id

    @property
    def time(self) -> int:
        """The unix timestamp of when the message was posted.

        :rtype: int"""
        return self._time

    @property
    def sender(self) -> SessionView:
        """The view of the sender's session.

        :rtype: euphoria.SessionView"""
        return self._sender

    @property
    def content(self) -> str:
        """The content of the message (client-defined).

        :rtype: str"""
        return self._content

    @property
    def encryption_key_id(self) -> str:
        """The id of the key that encrypts the message in storage. Potentially
        None.

        :rtype: str"""
        return self._encryption_key_id

    @property
    def edited(self) -> int:
        """The unix timestamp of when the message was last edited. Potentially
        None.

        :rtype: int"""
        return self._edited

    @property
    def deleted(self) -> int:
        """The unix timestamp of when the message was deleted. Potentially
        None.

        :rtype: int"""
        return self._deleted

    @property
    def truncated(self) -> bool:
        """If true, then the full content of this message is not included.

        :rtype: bool"""
        return self._truncated


class Message(MessageBased):
    """A Message is a node in a Room's Log. It corresponds to a chat message,
    or a post, or any broadcasted event in a room that should appear in the log."""
    pass


class HelloEvent:
    """A HelloEvent is sent by the server to the client when a session is
    started. It includes information about the client's authentication and
    associated identity."""

    def __init__(self, j: dict):
        self._id = j['id']
        self._account = j.get('account', None)
        self._session = SessionView(j['session'])
        self._account_has_access = j.get('account_has_access', True)
        self._room_is_private = j.get('room_is_private')
        self._version = j.get('version')

    @property
    def id(self) -> str:
        """The id of the agent or account logged into this session.

        :rtype: str"""
        return self._id

    @property
    def account(self) -> dict:
        """Details about the user's account, if the session is logged in. None
        otherwise.

        :rtype: dict"""
        return self._account

    @property
    def session(self) -> SessionView:
        """A :py:class:`euphoria.SessionView` describing the session.

        :rtype: euphoria.SessionView"""
        return self._session

    @property
    def account_has_access(self) -> bool:
        """If true, then the account has an explicit access grant to the current room.

        :rtype: bool"""
        return self._account_has_access

    @property
    def room_is_private(self) -> bool:
        """If true, the session is connected to a private room.

        :rtype: bool"""
        return self._room_is_private

    @property
    def version(self) -> str:
        """The version of the code being run and served by the server.

        :rtype: str"""
        return self._version


class PingEvent:
    """A PingEvent represents a server-to-client ping. The client should send
     back a ping-reply with the same value for the time field as soon as
     possible (or risk disconnection)."""

    def __init__(self, j: dict):
        self._time = j['time']
        self._next = j['next']

    @property
    def time(self) -> int:
        """A unix timestamp according to the server's clock.

        :rtype: int"""
        return self._time

    @property
    def next(self) -> int:
        """The expected time of the next ping-event, according to the server's clock.

        :rtype: int"""
        return self._next


class BounceEvent:
    """A BounceEvent indicates that access to a room is denied."""

    def __init__(self, j: dict):
        self._reason = j.get('reason', None)
        self._auth_options = j.get('auth_options', None)

    @property
    def reason(self) -> str:
        """The reason why access was denied. Potentially None.

        :rtype: str"""
        return self._reason

    @property
    def auth_options(self) -> list:
        """A list of authentication options that may be used. Potentially None.

        :rtype: list"""
        if not self._auth_options:
            return ["passcode"]
        return self._auth_options


class AuthReply:
    """An AuthReply reports whether the auth command succeeded."""

    def __init__(self, j: dict):
        self._success = j['success']
        self._reason = j.get('reason', None)

    @property
    def success(self) -> bool:
        """True if authentication succeeded.

        :rtype: bool"""
        return self._success

    @property
    def reason(self) -> str:
        """If AuthReply.success was false, the reason for failure.

        :rtype: str"""
        return self._reason


class SnapshotEvent:
    """A SnapshotEvent indicates that a session has successfully joined a room.
    It also offers a snapshot of the room's state and recent history."""

    def __init__(self, j: dict):
        self._identity = j['identity']
        self._session_id = j['session_id']
        self._version = j['version']
        self._listing = [SessionView(sub_j) for sub_j in j['listing']]
        self._log = [Message(sub_j) for sub_j in j['log']]

    @property
    def identity(self) -> str:
        """The id of the agent or account logged into this session.

        :rtype: str"""
        return self._identity

    @property
    def session_id(self) -> str:
        """The globally unique id of this session.

        :rtype: str"""
        return self._session_id

    @property
    def version(self) -> str:
        """The server's version identifier.

        :rtype: str"""
        return self._version

    @property
    def listing(self) -> List[SessionView]:
        """The list of all other sessions joined to the room (excluding this session.)

        :return: A list of :py:class:`euphoria.SessionView`
        :rtype: list"""
        return self._listing

    @property
    def log(self) -> List[Message]:
        """The most recent messages posted to the room (currently up to 100.)

        :return: A list of :py:class:`euphoria.Message`
        :rtype: list"""
        return self._log


class NetworkEvent:
    def __init__(self, j: dict):
        self._type = j['type']
        self._server_id = j['server_id']
        self._server_era = j['server_era']

    @property
    def type(self) -> str:
        """The type of network event; for now, always 'partition'.

        :rtype: str"""
        return self._type

    @property
    def server_id(self) -> str:
        """The id of the affected server.

        :rtype: str"""
        return self._server_id

    @property
    def server_era(self) -> str:
        """The era of the affected server.

        :rtype: str"""
        return self._server_era

class NickBased:

    def __init__(self, j: dict):
        self._session_id = j['session_id']
        self._id = j['id']
        self._from = j['from']
        self._to = j['to']

    @property
    def session_id(self) -> str:
        """The id of the session this name applies to.

        :rtype: str"""
        return self._session_id

    @property
    def id(self) -> str:
        """The id of the agent or account logged into the session.

        :rtype: str"""
        return self._id

    @property
    def from_(self) -> str:
        """The previous name associated with the session.

        :rtype: str"""
        return self._from

    @property
    def to(self) -> str:
        """The name associated with the session henceforth.

        :rtype: str"""
        return self._to

class NickEvent(NickBased):
    """A NickEvent indicates that a session successfully changed their nick."""
    pass


class NickReply(NickBased):
    """A NickReply indicates that you successfully changed your nick."""
    pass

class SendEvent(MessageBased):
    """A SendEvent indicates a message received by the room from another session."""
    pass

class EditMessageEvent(MessageBased):
    """An EditMessageEvent indicates that a message in the room has been modified or deleted."""


class SendReply(MessageBased):
    """A SendReply indicates that you successfully sent a message."""


class JoinEvent(SessionViewBased):
    """A JoinEvent indicates a session just joined the room."""

class PartEvent(SessionViewBased):
    """A PartEvent indicates a session just disconnected from the room."""

DATA_TYPES = {'hello-event': HelloEvent,
              'snapshot-event': SnapshotEvent,
              'ping-event': PingEvent,
              'bounce-event': BounceEvent,
              'auth-reply': AuthReply,
              'network-event': NetworkEvent,
              'nick-event': NickEvent,
              'nick-reply': NickReply,
              'send-event': SendEvent,
              'edit-message-event': EditMessageEvent,
              'send-reply': SendReply,
              'join-event': JoinEvent,
              'part-event': PartEvent}
