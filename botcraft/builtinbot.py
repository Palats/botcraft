import gflags
from twisted.internet import reactor, protocol, defer

import botcraft
from . import main
from . import minecraft
from . import botproto


FLAGS = gflags.FLAGS


class Bot(object):
    def __init__(self):
        self.mcbot = minecraft.MCBot()
        self.mcbot.toBot = self.fromServer

    def fromServer(self, **kwargs):
        pass

    def toServer(self, **kwargs):
        self.mcbot.fromBot(**kwargs)

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

        self.toServer(msgtype=botproto.CONNECT,
                      username=self.username,
                      hostname=self.hostname,
                      port=self.port)

        botcraft.run()
