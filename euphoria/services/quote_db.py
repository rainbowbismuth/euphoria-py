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

import re
import shelve

from euphoria import Bot, Packet
from tiny_agent import Agent


# Currently only works in a public room


class Service(Agent):
    def __init__(self, bot: Bot):
        super(Service, self).__init__(loop=bot.loop)
        bot.add_listener(self)
        self._bot = bot
        self._set_re = re.compile("!quote set (.*)")
        self._get_re = re.compile("!quote get (.*)")
        self._del_re = re.compile("!quote delete (.*)")

    @Agent.send
    async def on_packet(self, packet: Packet):
        send_event = packet.send_event
        if send_event and send_event.content.startswith("!quote"):
            set_match = self._set_re.match(send_event.content)
            if set_match:
                name = set_match.group(1)
                parent = await self._bot.send_get_message(send_event.parent)
                message = parent.data
                with shelve.open('quotes.db', 'c') as db:
                    db[name] = "{0}: {1}".format(message.sender.name, message.content)
                self._bot.send_content("acknowledged!", parent=send_event.id)
                return

            get_match = self._get_re.match(send_event.content)
            if get_match:
                name = get_match.group(1)
                with shelve.open('quotes.db', 'r') as db:
                    if name in db:
                        self._bot.send_content(db[name], parent=send_event.id)
                    else:
                        self._bot.send_content("sorry, no quote exists with that name", parent=send_event.id)
                return

            del_match = self._del_re.match(send_event.content)
            if del_match:
                name = del_match.group(1)
                with shelve.open('quotes.db', 'w') as db:
                    if name in db:
                        del db[name]
                        self._bot.send_content("quote deleted", parent=send_event.id)
                    else:
                        self._bot.send_content("sorry, no quote exists with that name", parent=send_event.id)
                return

            self._bot.send_content("usage: !quote [set|get|delete] quote_name", parent=send_event.id)
