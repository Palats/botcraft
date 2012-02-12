"""Botcraft protocol tools."""


# Message types
# All have msgtype

# Server -> Bot
SERVER_JOINED = 'SERVER_JOINED'
CHAT_MESSAGE = 'CHAT_MESSAGE'
POSITION_CHANGED = 'POSITION_CHANGED'

# Bot -> Server
CONNECT = 'CONNECT'
SEND_CHAT = 'SEND_CHAT'
DO_MOVE = 'DO_MOVE'


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


