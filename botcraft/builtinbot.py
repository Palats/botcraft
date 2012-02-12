import logging

import gflags
from twisted.internet import reactor, protocol, defer

import botcraft
from . import minecraft
from . import botproto


logger = logging.getLogger(__name__)
FLAGS = gflags.FLAGS


class Bot(object):
    def __init__(self):
        self.mcbot = minecraft.MCBot()
        self.mcbot.toBot = self.fromServer

    def fromServer(self, msg):
        """Process message received from the botcraft server.

        Args:
            msg: botproto.Message, the message object received from the server.
        """
        # As long as the server is trusted, we can blindly call methods.
        # Otherwise it might go a bit wrong - but the prefixing with 'on'
        # should reduce any risk if the assumption changes.
        method_name = 'on' + msg.msgtype
        if hasattr(self, method_name):
            getattr(self, method_name)(msg)
        else:
            logging.error('Unknown msgtype %r', msg.msgtype)

    def toServer(self, msg):
        """Send the given message to the botcraft server."""
        self.mcbot.fromBot(msg)

    def main(self):
        gflags.DEFINE_string(
                'username', '',
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

        self.username = FLAGS.username
        self.hostname = FLAGS.hostname
        self.port = FLAGS.port

        self.toServer(botproto.Connect(
            username=self.username,
            hostname=self.hostname,
            port=self.port))

        botcraft.run()

    def onChatMessage(self, msg):
        pass

    def onPositionChanged(self, msg):
        pass
