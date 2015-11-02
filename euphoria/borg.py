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
import logging.config
from typing import Mapping

import yaml

from euphoria import Bot, BotConfig
from tiny_agent import SupervisorOneForOne

logger = logging.getLogger(__name__)

__all__ = ['BorgConfig']


class BorgConfig:
    def __init__(self, dictionary: dict = None, filename: str = None):
        if filename:
            assert dictionary is None
            with open(filename) as f:
                dictionary = yaml.load(f)

        conf = dictionary['borg']
        self._dict = {}
        for key, value in conf.items():
            bot_conf = BotConfig(dictionary=value)
            self._dict[key] = bot_conf

    @property
    def bots(self) -> Mapping[str, BotConfig]:
        return self._dict


def make_bot_constructor(config, loop):
    def construct():
        return Bot(config, loop=loop)

    return construct


def main():
    logging.config.dictConfig(yaml.load(open('logging.yml').read()))
    loop = asyncio.get_event_loop()
    borg_config = BorgConfig(filename='borg.yml')
    one_for_one = SupervisorOneForOne(loop=loop)
    for name, bot_config in borg_config.bots.items():
        one_for_one.add_child(name, make_bot_constructor(bot_config, loop))

    loop.run_until_complete(one_for_one.task)
    logger.info("main() borg shutdown!")
    loop.run_until_complete(asyncio.wait(asyncio.Task.all_tasks(loop=loop)))  # Let everything else shutdown cleanly


if __name__ == '__main__':
    main()
