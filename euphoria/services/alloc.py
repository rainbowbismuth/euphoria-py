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

"""Say '!alloc' to see some neat memory statistics"""

import linecache
import os
import tracemalloc

import tiny_agent
from euphoria import Bot, Packet
from tiny_agent import Agent

tracemalloc.start()


def display_top(snapshot, group_by='lineno', limit=10):
    lines = []
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
        tracemalloc.Filter(False, tracemalloc.__file__),
        tracemalloc.Filter(False, linecache.__file__)
    ))
    top_stats = snapshot.statistics(group_by)

    lines.append("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        lines.append("#%s: %s:%s: %.1f KiB"
                     % (index, filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            lines.append('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        lines.append("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    lines.append("Total allocated size: %.1f KiB" % (total / 1024))
    return '\n'.join(lines)


class Service(Agent):
    def __init__(self, bot: Bot):
        super(Service, self).__init__(loop=bot.loop)
        bot.add_listener(self)
        self._bot = bot

    @tiny_agent.send
    async def on_packet(self, packet: Packet):
        send_event = packet.send_event
        if send_event and send_event.content.startswith("!alloc"):
            snapshot = tracemalloc.take_snapshot()
            line = display_top(snapshot)
            await self._bot.send_content(line, parent=send_event.id)
