from . import minecraft
from . import main


class Bot(object):
    def __init__(self):
        self.mcproto = minecraft.MCBot()
        self.mcproto.toBot = self.fromServer

    def fromServer(self, **kwargs):
        pass

    def toServer(self, **kwargs):
        self.mcproto.fromBot(**kwargs)

    def main(self):
        main.main(self.mcproto)
