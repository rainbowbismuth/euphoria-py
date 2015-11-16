# euphoria-py v0.7
[![Build Status](https://travis-ci.org/rainbowbismuth/euphoria-py.svg)](https://travis-ci.org/rainbowbismuth/euphoria-py)

An asyncio based euphoria.io bot library and framework for Python 3.5 and newer, ONLY. Make sure you are using the right
version of pip and the python interpreter.

API is expected to undergo major additions currently, and the documentation isn't all there yet.

[Documentation](http://rainbowbismuth.github.io/euphoria-py/docs/)

## Installation

To install the dependencies needed to run euphoria-py, install everything in requirements.txt

```shell
pip install -r requirements.txt
```

### Extras

If using the euphoria.services.reddit_notify service, you must install The Pythonic Reddit API Wrapper (PRAW) as well.

```shell
pip install praw
```

## Configuration

Edit bot.yml

```yml
bot:
  room: room-on-euphoria.io
  # The passcode option can be deleted for a public room
  passcode: password-to-private-room
  nick: bot-nickname
  services:
    # Gives you access to commands like !ping @botname, !kill @botname and !uptime @botname
    botrulez: euphoria.services.botrulez
    # Lets the bot send you reminders later, like !remind 15m take out the trash
    reminder: euphoria.services.reminder
    # Some services might take an extended set of options like reddit_notify
    reddit_notify:
      module: euphoria.services.reddit_notify
      reddit_agent: euphoria-py utility that notifies about new reddit posts
      subreddits: [pics, programming, funny]
      daily_thread: True
```

The bog logs information to the console and to a rotating log file by default, you can edit the configuration
in logging.yml (It uses the standard python logging framework, see the official documentation)

## Running

From this directory run:

```shell
python -m euphoria.bot
```
