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

"""A high-level easy to use bot interface."""

import asyncio
import datetime
import importlib
import logging
import logging.config
from asyncio import AbstractEventLoop, Future
from typing import Optional

import yaml

from euphoria import Client, NickAndAuth
from tiny_agent import Agent, SupervisorOneForOne
from .client import EUPHORIA_URL

__all__ = ['BotConfig', 'Bot']

logger = logging.getLogger(__name__)


# TODO: Add Ctrl-C handler, see https://github.com/rainbowbismuth/euphoria-py/issues/4


class BotConfig:
    """A collection of options to configure a :py:class:`euphoria.Bot` with.

    Supply either the dictionary or the filename parameter.

    :param dict dictionary: A dictionary of config options
    :param str filename: A path to a YAML file containing the config options
    """

    def __init__(self, dictionary: dict = None, filename: str = None):
        if filename:
            assert dictionary is None
            with open(filename) as f:
                dictionary = yaml.load(f)

        conf = dictionary['bot']
        self._room = conf['room']
        self._nick = conf['nick']
        self._passcode = conf.get('passcode', "")
        self._uri_format = conf.get('uri_format', EUPHORIA_URL)
        self._services_max_restarts = conf.get('services_max_restarts', 3)
        self._services_max_restarts_period = conf.get('services_max_restarts_period', 15.0)
        self._services = conf.get('services', {})

    @property
    def room(self) -> str:
        """The name of the room the bot should spawn in.

        Doesn't have a default.

        :rtype: str
        """
        return self._room

    @property
    def nick(self) -> str:
        """The initial nick the bot should have.

        Doesn't have a default.

        :rtype: str
        """
        return self._nick

    @property
    def passcode(self) -> str:
        """The passcode to the room if one is necessary.

        Defaults to the empty string

        :rtype: str
        """
        return self._passcode

    @property
    def uri_format(self) -> str:
        """The URI to connect to after being formatted with the room name.

        Defaults to "wss://euphoria.io:443/room/{0}/ws"

        :rtype: str
        """
        return self._uri_format

    @property
    def services_max_restarts(self) -> int:
        return self._services_max_restarts

    @property
    def services_max_restarts_period(self) -> float:
        return self._services_max_restarts_period

    @property
    def services(self) -> dict:
        """A mapping from service names, to a python module path.

        Defaults to an empty map.

        :rtype: dict
        """
        return self._services


def make_service_constructor(mod, bot):
    # Got caught by python's closure late binding...
    def construct():
        return mod.Service(bot)

    return construct


class Bot(Agent):
    def __init__(self, config: BotConfig, loop: AbstractEventLoop = None):
        super(Bot, self).__init__(loop=loop)
        self._config = config
        self._client = Client(config.room, config.uri_format, handle_pings=True, loop=loop)
        self._nick_and_auth = NickAndAuth(self._client, config.nick, config.passcode)
        self._service_supervisor = SupervisorOneForOne(max_restarts=config.services_max_restarts,
                                                       period=config.services_max_restarts_period, loop=loop)
        self._start_time = datetime.datetime.now()

        for short_name, module_path in config.services.items():
            mod = importlib.import_module(module_path)
            self._service_supervisor.add_child(short_name, make_service_constructor(mod, self))

        self.bidirectional_link(self._client)
        self.bidirectional_link(self._nick_and_auth)
        self.bidirectional_link(self._service_supervisor)

        self._client.connect()

    @property
    def config(self) -> BotConfig:
        """Returns the dictionary this bot was configured with.

        :rtype: euphoria.BotConfig"""
        return self._config

    @property
    def start_time(self) -> datetime.date:
        """Returns the time that the Bot was started.

        :rtype: datetime.date"""
        return self._start_time

    @property
    def current_nick(self) -> str:
        return self._nick_and_auth.current_nick

    @property
    def desired_nick(self) -> str:
        return self._nick_and_auth.desired_nick

    @property
    def passcode(self) -> str:
        return self._nick_and_auth.passcode

    @property
    def connected(self) -> bool:
        return self._client.connected

    @property
    def authorized(self) -> bool:
        return self._nick_and_auth.authorized

    @Agent.call
    async def set_desired_nick(self, new_nick: str) -> Optional[str]:
        return await self._nick_and_auth.set_desired_nick(new_nick)

    @Agent.call
    async def set_passcode(self, new_passcode: str) -> Optional[str]:
        return await self._nick_and_auth.set_passcode(new_passcode)

    def send_content(self, content: str, parent: Optional[str] = None) -> Future:
        return self._client.send_content(content, parent)

    def add_listener(self, listener: Agent):
        self._client.add_listener(listener)


def main():
    logging.config.dictConfig(yaml.load(open('logging.yml').read()))
    loop = asyncio.get_event_loop()
    config = BotConfig(filename='bot.yml')
    bot = Bot(config, loop=loop)

    loop.run_until_complete(bot.task)
    logger.info("main() bot shutdown!")
    loop.run_until_complete(asyncio.wait(asyncio.Task.all_tasks(loop=loop)))  # Let everything else shutdown cleanly


if __name__ == '__main__':
    main()
