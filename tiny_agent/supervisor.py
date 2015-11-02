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
import logging
from asyncio import AbstractEventLoop
from typing import Optional, Callable

from tiny_agent import Agent

__all__ = ['SupervisorOneForOne', 'SupervisorOneForAll', 'Restart', 'TooManyRestarts']

logger = logging.getLogger(__name__)


class Restart(Exception):
    pass


class TooManyRestarts(Exception):
    pass


class SupervisorOneForOne(Agent):
    def __init__(self, period: float = 60.0, max_restarts: int = 3, loop: AbstractEventLoop = None):
        super(SupervisorOneForOne, self).__init__(loop=loop)
        self._max_restarts = max_restarts
        self._period = period
        self._period_task = None
        self._children = {}
        self._agent_to_name = {}
        self._name_to_agent = {}

    @Agent.send
    async def add_child(self, name: str, factory: Callable[[], Agent]):
        assert name not in self._children
        child = factory()
        self.monitor(child)
        self._children[name] = (factory, 0)
        self._agent_to_name[child] = name
        self._name_to_agent[name] = child

    async def _period_task_body(self):
        await asyncio.sleep(self._period)
        if self.alive:
            for key in self._children.keys():
                (factory, _) = self._children[key]
                self._children[key] = (factory, 0)
        self._period_task = None

    @Agent.send
    async def on_monitored_exit(self, who: Agent, exc: Optional[Exception]):
        assert who in self._agent_to_name
        name = self._agent_to_name[who]
        logger.info("%s: the agent %s named %s stopped because %s", self, who, name, exc)
        (factory, num) = self._children[name]
        if num >= self._max_restarts:
            raise TooManyRestarts

        if self._period_task:
            self._period_task.cancel()
        self._period_task = asyncio.ensure_future(self._period_task_body(), loop=self._loop)

        new_child = factory()
        self.monitor(new_child)
        self._children[name] = (factory, num + 1)
        self._agent_to_name[new_child] = name
        self._name_to_agent[name] = new_child

    @Agent.call
    async def get(self, name: str, default: Optional[Agent] = None) -> Optional[Agent]:
        return self._name_to_agent.get(name, default)


class SupervisorOneForAll(Agent):
    def __init__(self, loop: AbstractEventLoop = None):
        super(SupervisorOneForAll, self).__init__(loop=loop)
        self._children = {}
        self._agent_to_name = {}
        self._name_to_agent = {}
        self._restarts = 0

    @Agent.send
    async def add_child(self, name: str, factory: Callable[[], Agent]):
        assert name not in self._children
        child = factory()
        self.monitor(child)
        self._children[name] = factory
        self._agent_to_name[child] = name
        self._name_to_agent[name] = child

    @Agent.send
    async def on_monitored_exit(self, who: Agent, exc: Optional[Exception]):
        if who not in self._agent_to_name:
            return
        if exc:
            logger.info("%s: the agent %s stopped because %s", self, who, exc)
        else:
            logger.info("%s: the agent %s stopped normally.", self, who)
        if self._restarts >= 3:
            raise TooManyRestarts
        self._restarts += 1

        for old_child in self._agent_to_name.keys():
            old_child.exit(Restart())

        for name, factory in self._children.items():
            self.add_child(name, factory)

        self._children = {}
        self._agent_to_name = {}
        self._name_to_agent = {}

    @Agent.call
    async def get(self, name: str, default: Optional[Agent] = None) -> Optional[Agent]:
        return self._name_to_agent.get(name, default)
