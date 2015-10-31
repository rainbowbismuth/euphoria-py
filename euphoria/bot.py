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
import importlib
import logging
import logging.config

import yaml

from .client import Client, EUPHORIA_URL
from .state_machines import NickAndAuth

logger = logging.getLogger(__name__)


# TODO: Add closed property? and wait until closed? + started etc?
# TODO: Add Ctrl-C handler, see https://github.com/rainbowbismuth/euphoria-py/issues/4
# TODO: What am I doing with _exit_exc?


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
        self._handle_pings = conf.get('handle_pings', True)
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
    def handle_pings(self) -> bool:
        """Returns whether or not the bot should handle pings for you.

        Defaults to True.

        :rtype: bool
        """
        return self._handle_pings

    @property
    def services(self) -> dict:
        """A mapping from service names, to a python module path.

        Defaults to an empty map.

        :rtype: dict
        """
        return self._services


class Bot:
    """A high-level bot for euphoria.

    :param euphoria.BotConfig config: Bot configuration
    :param asyncio.AbstractEventLoop loop: The asyncio event loop you want to use
    """

    def __init__(self, config: BotConfig, loop: asyncio.AbstractEventLoop = None):
        self._config = config
        self._client = Client(config.room, config.uri_format, config.handle_pings, loop=loop)
        self._nick_and_auth = NickAndAuth(self._client, config.nick)
        self._nick_and_auth.passcode = config.passcode
        self._service_creators = {}
        self._services = {}
        self._exit_exc = None

        for name, path in config.services.items():
            mod = importlib.import_module(path)
            self.add_service_creator(name, mod.main)

    def __repr__(self) -> str:
        fmt = "<euphoria.Bot room='{0}' nick='{1}'>"
        return fmt.format(self._client.room, self._nick_and_auth.desired_nick)

    @property
    def config(self) -> BotConfig:
        """Returns the dictionary this bot was configured with.

        :rtype: euphoria.BotConfig"""
        return self._config

    @property
    def client(self) -> Client:
        """Returns the associated Client this bot is using.

        :rtype: euphoria.Client"""
        return self._client

    @property
    def nick_and_auth(self) -> NickAndAuth:
        """Returns the associated NickAndAuth this bot is using.

        :rtype: euphoria.state_machines.NickAndAuth"""
        return self._nick_and_auth

    def add_service_creator(self, name: str, f):
        """Add a coroutine creating function that takes a bot under name.

        :param str name: The short form name of the service creator
        :param f: An async function that is called f(bot)"""
        assert name not in self._service_creators
        self._service_creators[name] = f

    def start_service(self, name: str):
        """Starts the service called name.

        :param str name: The short form name of the service to start"""
        creator = self._service_creators[name]

        async def try_service():
            try:
                await creator(self)
            except asyncio.CancelledError:
                return
            except SystemExit as exc:
                self._exit_exc = exc
                self.close()
                return
            except:
                logger.error("%s service %s crashed",
                             self, name, exc_info=True)
                # Retry the service. This should eventually stack overflow
                # and thats probably good enough for now...
                # TODO: FIX
                if not self.client.closed:
                    await try_service()

        if name in self._services:
            self._services[name].cancel()
        task = asyncio.ensure_future(try_service(), loop=self._client.loop)
        logger.info("%s started service %s", self, name)
        self._services[name] = task

    def stop_service(self, name: str):
        """Stops the service called name.

        :param str name: The name of the service to stop"""
        if name in self._services:
            self._services[name].cancel()
            self._services[name] = None
            logger.info("%s stopped service %s", self, name)

    def contains_service(self, name: str) -> bool:
        """Returns whether or not this bot has a particular running service.

        :param str name: The name of the service to check"""
        return name in self._services

    def get_service(self, name: str) -> asyncio.Task:
        """Retrieves a service's task.

        :param str name: The name of the service to get
        :rtype: asyncio.Task"""
        return self._services[name]

    def start_all(self):
        """Start all services.

        Currently restarts those already started."""
        for key in self._service_creators.keys():
            self.start_service(key)

    def stop_all(self):
        """Stop all services."""
        for key in self._service_creators.keys():
            self.stop_service(key)

    def close(self):
        """Close the bot."""
        logger.info("%s closing", self)
        self._nick_and_auth.close()
        self._client.close()
        self.stop_all()

    def start(self):
        """Start the bot."""
        asyncio.ensure_future(self._nick_and_auth.start(),
                              loop=self._client.loop)
        asyncio.ensure_future(self._client.start(), loop=self._client.loop)
        self.start_all()


async def main(config_file: str = 'bot.yml', loop: asyncio.AbstractEventLoop = None):
    """Run a Bot with restarts.

    This method is a `coroutine <https://docs.python.org/3/library/asyncio-task.html#coroutines>`_."""
    config = BotConfig(filename=config_file)
    tries = 0
    while True:
        bot = None
        try:
            bot = Bot(config, loop=loop)
            bot.start()
            await bot.client.wait_until_closed()
        except asyncio.CancelledError:
            pass
        except SystemExit as exc:
            bot._exit_exc = exc
            bot.close()
        except:
            logger.error("%s bot crashed", bot, exc_info=True)
            tries += 1
            if tries > 5:
                break
        finally:
            break


if __name__ == '__main__':
    logging.config.dictConfig(yaml.load(open('logging.yml').read()))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop=loop))
    tasks = asyncio.Task.all_tasks(loop=loop)
    for task in tasks:
        task.cancel()
    loop.run_until_complete(asyncio.wait(tasks))
    loop.stop()
    loop.close()
