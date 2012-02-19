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
        self.position = None
        self.state = None
        self.mcbot = minecraft.MCBot(self.fromServer)

    def setState(self, state, *args):
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
        d = defer.Deferred()
        msg.client_tag = d
        reactor.callLater(0, self.mcbot.fromBot, msg)
        return d

    def onPositionChanged(self, msg):
        self.position = botproto.Position(msg.position)

    def onServerJoined(self, msg):
        self.state = self.stateJoined

    def stateJoined(self, msg):
        pass

    def start(self, username, hostname, port):
        self.username = username
        self.hostname = hostname
        self.port = port
        self.send(botproto.Connect(
            username=self.username,
            hostname=self.hostname,
            port=self.port))

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

        self.start(FLAGS.username, FLAGS.hostname, FLAGS.port)

        botcraft.run()
