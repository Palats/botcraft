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
        self.mcbot = minecraft.MCBot(self.fromServer)

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
            return True
        else:
            logging.info('Unhandled msgtype %r', msg.msgtype)
            return False

    #def toServer(self, msg):
    #    """Send the given message to the botcraft server."""
    #    return self.mcbot.fromBot(msg)

    # Convenience shortcut
    def send(self, msg):
        #reactor.callLater(0, self.mcbot.fromBot, msg)
        return self.mcbot.fromBot(msg)

    def main(self):
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

        self.username = FLAGS.username
        self.hostname = FLAGS.hostname
        self.port = FLAGS.port

        self.send(botproto.Connect(
            username=self.username,
            hostname=self.hostname,
            port=self.port))

        botcraft.run()
