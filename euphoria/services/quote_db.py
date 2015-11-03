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
import tiny_agent

class Quote:
    def __init__(self, sender, content, time):
        self._sender = sender
        self._content = content
        self._time = time

    @property
    def sender(self):
        return self._sender

    @property
    def content(self):
        return self._content

    @property
    def joined(self):
        return "[ {0} ] {1}".format(self.sender, self.content)

    @property
    def time(self):
        return self._time


class Service(Agent):
    def __init__(self, bot: Bot, _: dict):
        super(Service, self).__init__(loop=bot.loop)
        bot.add_listener(self)
        self._bot = bot
        self._set_re = re.compile("!quote set (.*)")
        self._get_re = re.compile("!quote get (.*)")
        self._del_re = re.compile("!quote delete (.*)")
        self._find_re = re.compile("!quote find (.*)")

    @tiny_agent.send
    async def find(self, regex: str, parent: str):
        output = []
        with shelve.open('quotes.db', 'r') as db:
            compiled = re.compile(regex)
            for key in db.keys():
                if compiled.search(key):
                    output.append("found match in name: " + key)
                if key in db:
                    record = db[key]
                    if compiled.search(record.sender):
                        output.append("found match in sender: " + key)
                    if compiled.search(record.content):
                        output.append("found match in content: " + key)
                if len(output) >= 5:
                    output.append("search limited to the first few results")
                    break
        if output:
            self._bot.send_content('\n'.join(output), parent=parent)
        else:
            self._bot.send_content('no matches found, sorry', parent=parent)

    @tiny_agent.send
    async def on_packet(self, packet: Packet):
        send_event = packet.send_event
        if send_event and send_event.content.startswith("!quote"):
            set_match = self._set_re.match(send_event.content)
            if set_match:
                name = set_match.group(1)
                parent = await self._bot.send_get_message(send_event.parent)
                message = parent.data
                with shelve.open('quotes.db', 'c') as db:
                    if name in db:
                        self._bot.send_content("a quote already exists with this name", parent=send_event.id)
                    else:
                        db[name] = Quote(sender=message.sender.name, content=message.content, time=message.time)
                        self._bot.send_content("acknowledged!", parent=send_event.id)
                return

            get_match = self._get_re.match(send_event.content)
            if get_match:
                name = get_match.group(1)
                with shelve.open('quotes.db', 'r') as db:
                    if name in db:
                        self._bot.send_content(db[name].joined, parent=send_event.id)
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

            find_match = self._find_re.match(send_event.content)
            if find_match:
                regex = find_match.group(1)
                self.find(regex, send_event.id)
                return

            self._bot.send_content("usage: !quote [ set | get | delete ] quote_name\n"
                                   "usage: !quote find text_or_regex", parent=send_event.id)
