# Copyright (C) 2012 Pierre Palatin

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License v2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Base class for python based bots.

See botcraft_examples for implementation examples.
"""


import logging

import gflags
from twisted.internet import reactor, defer

import botcraft
from . import minecraft
from . import botproto


logger = logging.getLogger(__name__)
FLAGS = gflags.FLAGS


class Bot(object):
    """Base class for python bots.

    This class is made to be inherited from. It only keeps track of the current
    position and provide basic state machine functionnality.

    Attributes:
        position: botproto.Position, current known position of the bot. This is
            not necessarely up to date.
        state: function, what to call when a message is received. Return value
            of this function, if not None, will be the new state.
        mcbot: minecraft.MCBot, the mcbot instance doing the protocol heavy lifting.
    """
    def __init__(self):
        self.username = 'unknown'
        self.hostname = None
        self.port = None
        self.position = None
        self.state = None
        self.mcbot = minecraft.MCBot(self.fromServer)

    def setState(self, state):
        """Set new function to be called when a message from botcraft is received."""
        oldstate = self.state
        self.state = state
        logger.info('State %s -> %s', oldstate, self.state)

    def fromServer(self, msg):
        """Process message received from the botcraft server.

        The message is sent to 3 different things in succession:
         - Corresponding on<Event> method of the object, if present.
         - If it's a response to a message sent earlier, it will call any
           callback defined
         - And then it sends the message to the current state function,
           updating it if needed.

        Args:
            msg: botproto.Message, the message object received from the server.
        """
        # As long as the server is trusted, we can blindly call methods.
        # Otherwise it might go a bit wrong - but the prefixing with 'on'
        # should reduce any risk if the assumption changes.
        method_name = 'on' + msg.msgtype
        if hasattr(self, method_name):
            getattr(self, method_name)(msg)

        if msg.client_tag:
            msg.client_tag.callback(msg)

        if self.state:
            new_state = self.state(msg)
            if new_state is not None:
                self.setState(new_state)

    def send(self, msg, callback=None):
        """Send a message to botcraft server.

        Returns:
            defer.Deferred object. This will be called when botcraft decided to
            ack the actual message. Sending is asynchronous - it just queues up
            the message in twisted reactor.
         """
        callback = defer.Deferred()
        msg.client_tag = callback
        reactor.callLater(0, self.mcbot.fromBot, msg)
        return callback

    def onPositionChanged(self, msg):
        """Called when receiving a PositionChanged message.

        By default, update the current position of the bot.
        """
        self.position = botproto.Position(msg.position)

    def start(self, username, hostname, port):
        """Tell this bot to connect to the given server."""
        self.username = username
        self.hostname = hostname
        self.port = port
        self.send(botproto.Connect(
            username=self.username,
            hostname=self.hostname,
            port=self.port))

    def main(self):
        """Helper function to start this bot as standaline programm."""
        gflags.DEFINE_string(
                'username', 'unknown',
                'Bot name.',
                short_name='n')
        gflags.DEFINE_string(
                'hostname', 'localhost',
                'Minecraft server to connect to.',
                short_name='h')
        gflags.DEFINE_integer(
                'port', '25565',
                'Minecraft server port',
                short_name='p')

        botcraft.init()

        self.start(FLAGS.username, FLAGS.hostname, FLAGS.port)

        botcraft.run()
