"""Botcraft protocol tools."""


# Message types
# All have msgtype

class Message(object):
    client_tag = None

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
class Ack(ServerMessage):
    """Generic ack message for simple bot commands."""


class ServerJoined(ServerMessage):
    """Server has been joined."""
    pass

class ChatMessage(ServerMessage):
    """A chat message has been sent on the server.

    Your own messages will trigger this event too.
    """
    text = None
    username = None

    # If defined, it means that your Say() message was invalid.
    invalid_text = None


class PositionChanged(ServerMessage):
    """Bot changed position.

    This is sent either when arriving at destination after a successful move or
    because of an unwarrented move. Intermediate move do not trigger this event.
    """
    position = None

    # When this packet is sent has part of movement requested by the bot, False
    # will indicate that the movement failed.
    forced = None

# Bot -> Server
class Connect(BotMessage):
    """Connect to the given minecraft server.

    Response: ServerJoined
    """
    username = None
    hostname = None
    port = None

class Say(BotMessage):
    """Send something on chat.

    Response: ChatMessage
    """
    text = None

class Move(BotMessage):
    """Move to a new position.

    Response: PositionChanged
    """
    target = None


class SetActiveTool(BotMessage):
    """Set the current tool in creative mode.

    Response: Ack
    """

    item_id = None
    item_uses = None

class SetBlock(BotMessage):
    """Set the given block with new content.

    Response: Ack
    """

    x = None
    y = None
    z = None
    item_id = None
    item_uses = None


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

    def __str__(self):
        return 'Position(x=%s,y=%s,z=%s,stance=%s,yaw=%s,pitch=%s,on_ground=%s)' % (
                self.x, self.y, self.z, self.stance,
                self.yaw, self.pitch,
                self.on_ground)


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


