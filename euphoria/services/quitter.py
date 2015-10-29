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

"""Say !quit to call sys.exit() and shutdown"""

from euphoria import SendEvent
import sys

async def main(bot):
    client = bot.client
    stream = await client.stream()
    while True:
        send_event = await stream.skip_until(SendEvent)
        if send_event.data.content.startswith("!quit"):
            await client.send("goodbye!", parent=send_event.data.id)
            sys.exit()
