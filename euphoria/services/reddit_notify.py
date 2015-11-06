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
import re
import threading
from typing import List

import praw

import tiny_agent
from euphoria import Bot
from tiny_agent import Agent

logger = logging.getLogger(__name__)


class SubredditWatcher:
    def __init__(self, reddit: praw.Reddit, subreddit_name: str):
        self._reddit = reddit
        self._subreddit_name = subreddit_name
        self._subreddit = None
        self._previous = None

    def update(self, out: List[str]):
        if self._previous is None:
            self._subreddit = self._reddit.get_subreddit(self._subreddit_name)
            self._previous = next(self._subreddit.get_new())
            return

        submissions = []
        for submission in self._subreddit.get_new():
            if submission.created_utc <= self._previous.created_utc:
                break
            submissions.append(submission)
            if len(submissions) > 3:
                break
        if not submissions:
            return
        self._previous = submissions[0]
        fmt = "{0} New post to {1} by {2}: {3}"
        for submission in reversed(submissions):
            msg = fmt.format(submission.short_link,
                             submission.subreddit,
                             submission.author,
                             submission.title)
            out.append(re.sub('\s+', ' ', msg).strip())


class Service(Agent):
    @tiny_agent.init
    def __init__(self, bot: Bot, config: dict):
        super(Service, self).__init__(loop=bot.loop)
        self._bot = bot
        self._init(config)

    @tiny_agent.send
    async def _init(self, config: dict):
        assert "subreddits" in config, "This service must be configured with a list of subreddits"
        self._reddits = config["subreddits"]
        assert "reddit_agent" in config, "This service must be configured with a reddit_agent string"
        self._reddit_agent = config["reddit_agent"]
        self._reddit = praw.Reddit(self._reddit_agent)
        self._watchers = []
        for reddit_name in self._reddits:
            watcher = SubredditWatcher(self._reddit, reddit_name)
            self._watchers.append(watcher)
        for watcher in self._watchers:
            self._update_watcher(watcher)

    @tiny_agent.send
    async def _update_watcher(self, watcher: SubredditWatcher):
        out = []
        thread = threading.Thread(target=watcher.update, args=(out,), daemon=True)
        thread.start()
        while thread.is_alive():
            await asyncio.sleep(1.0)
        for msg in out:
            self._bot.send_content(msg)

        async def update_again():
            await asyncio.sleep(30.0)
            self._update_watcher(watcher)

        self.spawn_linked_task(update_again())
