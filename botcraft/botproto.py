"""Botcraft protocol tools."""


# Message types
# All have msgtype

class Message(object):
    def __init__(self, **kwargs):
        self.msgtype = self.__class__.__name__
        for k, v in kwargs.iteritems():
            assert hasattr(self, k)
            setattr(self, k, v)


class ServerMessage(Message):
    pass

class BotMessage(Message):
    pass


# Server -> Bot messages
class ServerJoined(ServerMessage):
    pass

class ChatMessage(ServerMessage):
    text = None
    username = None


class PositionChanged(ServerMessage):
    position = None

# Bot -> Server
class Connect(BotMessage):
    username = None
    hostname = None
    port = None

class Say(BotMessage):
    text = None


# Helper structures
class Position(object):
    def __init__(self, source=None):
        if source:
            self.x = source.x
            self.y = source.y
            self.z = source.z
            self.stance = source.stance
            self.yaw = source.yaw
            self.pitch = source.pitch
            self.on_ground = source.on_ground
        else:
            self.x = self.y = self.z = 0.0
            self.stance = 0.0
            self.yaw = self.pitch = 0.0
            self.on_ground = True

    def __eq__(self, other):
        return (self.x == other.x and
                self.y == other.y and
                self.z == other.z and
                self.stance == other.stance and
                self.yaw == other.yaw and
                self.pitch == other.pitch and
                self.on_ground == other.on_ground)

    def fromMessage(self, msg):
        self.x = msg['x']
        self.y = msg['y']
        self.z = msg['z']
        self.stance = msg['stance']
        self.yaw = msg['yaw']
        self.pitch = msg['pitch']
        self.on_ground = msg['on_ground']

    def toMessage(self):
        msg = {
                'x': self.x,
                'y': self.y,
                'z': self.z,
                'stance': self.stance,
                'yaw': self.yaw,
                'pitch': self.pitch,
                'on_ground': self.on_ground,
        }
        return msg


class Spawn(object):
    def __init__(self):
        self.x = self.y = self.z = 0.0

    def fromMessage(self, msg):
        self.x = msg['x']
        self.y = msg['y']
        self.z = msg['z']

    def toMessage(self):
        msg = {
                'x': self.x,
                'y': self.y,
                'z': self.z,
        }
        return msg


