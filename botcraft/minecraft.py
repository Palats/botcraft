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


"""Core implementation of botcraft protocol translator.

Botcraft provides a standard bot protocol. This module contains all the logic
allowing to interface botcraft protocol to a normal minecraft server.
"""


import logging
import re
import math
import collections
import Queue

from twisted.internet import reactor, protocol

from . import messages
from . import parsing
from . import packets
from . import botproto


logger = logging.getLogger(__name__)


class MCBotFactory(protocol.ReconnectingClientFactory):
    """Factory managing the connection to the minecraft server.

    It mainly takes care of reconnecting automatically. All the logic is in
    MCBot.
    """

    def __init__(self, protocol_func):
        self.protocol_func = protocol_func

    def startedConnecting(self, connector):
        print 'Started to connect.'

    def buildProtocol(self, addr):
        print 'Connected. (resetting reconnection delay)'
        self.resetDelay()
        return self.protocol_func()

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                                  reason)

    def onBuildProtocol(self):
        """Called back when requiring to connect/reconnect."""


class MCProtocol(protocol.Protocol):
    """Minecraft server protocol.

    This takes care of encoding/decoding packets, nothing more.
    When the connection is done, it calls the provided function with None.
    Every time a message is completely received, it will call the provided
    function with it.
    """
    def __init__(self, message_func):
        self.message_func = message_func
        self.protocol_id = None
        self.send_spec = None
        self.receive_spec = None
        self.stream = None

    def connectionMade(self):
        logger.debug('Protocol connectionMade.')

        self.protocol_id = 23
        self.send_spec = messages.protocol[self.protocol_id][0]
        self.receive_spec = messages.protocol[self.protocol_id][1]
        self.stream = parsing.Stream()

        self.message_func(None)

    def sendMessage(self, msg):
        """Send the given message to the minecraft server.

        Args:
            msg: {str:*}, see messages module for the details.
        """
        msgtype = msg['msgtype']
        msg_emitter = self.send_spec[msgtype]
        raw = msg_emitter.emit(msg)
        #logger.debug("Sending message (size %i): %s = %r", len(s), msg, s)
        self.transport.write(raw)

    def _parsePacket(self):
        """Parse a single packet out of stream, and return it."""
        try:
            # read Packet ID
            msgtype = parsing.parse_unsigned_byte(self.stream)
            if not self.receive_spec[msgtype]:
                raise parsing.UnsupportedPacketException(msgtype)
            logger.debug("Trying to parse message type %x" % (msgtype))
            msg_parser = self.receive_spec[msgtype]
            msg = msg_parser.parse(self.stream)
            msg['raw_bytes'] = self.stream.packet_finished()
            logger.debug("Received message (size %i): %s", len(msg['raw_bytes']), msg)
            return msg
        except parsing.PartialPacketException:
            return None

    def dataReceived(self, data):
        """Parse new bytes and notify for minecraft messages when complete."""
        self.stream.append(data)

        msg = self._parsePacket()
        while msg:
            self.message_func(msg)
            msg = self._parsePacket()



class MCBot(object):
    """Translator between minecraft server protocol and botcraft protocol.

    This class takes care of translating protocols. It takes care of keeping
    state and updating the bot as needed, while making minecraft happy through
    various keep alive, preventing fast moves and so on.
    """

    def __init__(self, bot_func):
        self.bot_func = bot_func

        self.username = None   # Overridden by the connect message
        self.tick = 0.050
        self.max_move_per_tick = 1.0

        self.delayed_call = None
        self.world_time = None

        self.spawn = botproto.Spawn()
        self.players = {}

        self.connected_tag = None

        self.current_position = botproto.Position()
        self.active_tool = {
                'item_id': 0x1,
                'count': 1,
                'uses': 0
        }

        self.target_position = None
        self.target_tag = None
        self._resetMove()

        self.connect_tag = None

        self.initialized = False

        self.factory = MCBotFactory(self.onBuildProtocol)
        self.protocol = None

        self.chat_tags = collections.defaultdict(Queue.Queue)

    def connect(self, host, port):
        """Connect the minecraft side."""
        reactor.connectTCP(host, port, self.factory)

    def onBuildProtocol(self):
        """Build a protocol when connecting/reconnecting to minecraft server."""
        self.protocol = MCProtocol(self.fromMinecraft)
        return self.protocol

    def toMinecraft(self, msg):
        """Send the given message to minecraft server."""
        self.protocol.sendMessage(msg)

    def fromMinecraft(self, msg):
        """Message received from minecraft server."""

        if msg is None:
            # Connection has just been established.
            self.toMinecraft({'msgtype': packets.HANDSHAKE, 'username': self.username})
        elif msg['msgtype'] == packets.KEEPALIVE:
            self.toMinecraft({'msgtype': packets.KEEPALIVE, 'id': 0})
        elif msg['msgtype'] == packets.LOGIN:
            pass
        elif msg['msgtype'] == packets.HANDSHAKE:
            logger.debug('Handshake done, hash: %s', msg['hash'])
            self.toMinecraft({
                'msgtype': packets.LOGIN,
                'proto_version': 23,
                'username': self.username,
                'nu1': 0,
                'nu2': 0,
                'nu3': 0,
                'nu4': 0,
                'nu5': 0,
                'nu6': 0,
                'nu7': '',
             })
        elif msg['msgtype'] == packets.CHAT:
            self.chatReceived(msg['chat_msg'])
        elif msg['msgtype'] == packets.UPDATETIME:
            self.world_time = msg['time']
        elif msg['msgtype'] == packets.SPAWNPOSITION:
            self.spawn.fromMessage(msg)
        elif msg['msgtype'] == packets.PLAYERPOSITIONLOOK:
            # When the server is unhappy about our position, we need to
            # acknowledge back.
            new_position = botproto.Position()
            new_position.fromMessage(msg)
            if new_position != self.current_position:
                self.current_position = new_position
                self.toBot(botproto.PositionChanged(
                    position=self.current_position,
                    client_tag=self.target_tag,
                    forced=True))
                self._resetMove()
                self._backgroundUpdate()

            if not self.initialized:
                self.initialized = True
                self.toBot(botproto.ServerJoined(client_tag=self.connect_tag))
        elif msg['msgtype'] == packets.PRECHUNK:
            # Remove the old chunk data, nothing to do really
            pass
        elif msg['msgtype'] == packets.CHUNK:
            logger.debug("Chunk %s,%s,%s", msg['x'], msg['y'], msg['z'])
        elif msg['msgtype'] == packets.PLAYERLIST:
            if msg['online']:
                self.players[msg['name']] = msg['ping']
                logger.debug('Player %s @ %s ms', msg['name'], msg['ping'])
            elif msg['name'] in self.players:
                self.players.pop(msg['name'])
        else:
            logger.info("Received message (size %i): %s", len(msg['raw_bytes']), msg)

    def toBot(self, msg):
        """Send the given message to the bot.

        This is asynchronous, the message is just queue in twisted reactor.
        """
        reactor.callLater(0, self.bot_func, msg)

    def fromBot(self, msg):
        """Dispatch a message coming from the bot."""
        if isinstance(msg, botproto.Connect):
            self.username = msg.username or self.username
            hostname = msg.hostname
            port = msg.port or None
            self.connect_tag = msg.client_tag
            self.connect(hostname, port)
        elif isinstance(msg, botproto.Say):
            if len(msg.text) > 100:
                self.toBot(botproto.ChatMessage(invalid_text='Too long', client_tag=msg.client_tag))
            else:
                text = msg.text[:100]
                self.chat_tags[text].put(msg.client_tag)
                msg = {'msgtype': packets.CHAT,
                       'chat_msg': msg.text[:100]}
                self.toMinecraft(msg)
        elif isinstance(msg, botproto.Move):
            self._resetMove()
            self.target_position = msg.target
            self.target_tag = msg.client_tag
        elif isinstance(msg, botproto.SetActiveTool):
            self.active_tool['item_id'] = msg.item_id
            self.active_tool['uses'] = msg.item_uses
            mcmsg = {
                    'msgtype': packets.CREATIVEACTION,
                    'slot': 36,
                    'details': self.active_tool,
            }
            self.toMinecraft(mcmsg)
            # There's no feedback on setting the active tool, so just send ok
            # directly.
            self.toBot(botproto.Ack(client_tag=msg.client_tag))
        elif isinstance(msg, botproto.SetBlock):
            self.setBlock(msg)

    def chatReceived(self, message):
        """Process a minecraft chat message, to send it to the bot."""
        logger.info('Chat message: %s', message)
        match = re.search('^<([^>]+)> (.*)$', message)
        if not match:
            logger.warning('Unknown chat message: %s', message)
            return
        username = match.group(1)
        text = match.group(2)

        tag = None
        if username == self.username and text in self.chat_tags:
            tag = self.chat_tags[text].get(None)

            if self.chat_tags[text].empty():
                # Remove empty queues so they don't accumulate for everything
                # that is said on chat. Checking empty() on a queue is not
                # thread proof, but given that we're using twisted here, and so
                # are not executing in parallel, we should be fine.
                del self.chat_tags[text]

        self.toBot(botproto.ChatMessage(username=username, text=text, client_tag=tag))

    def _resetMove(self):
        self.target_position = None
        self.target_tag = None

    def _backgroundUpdate(self):
        """Keep sending position to minecraft server.

        Minecraft server require a regular update of the position, or will
        deconnect any client.
        This method takes care of that, and check when the bot arrives at the
        current targeted destination.
        """
        if self.target_position:
            if self.target_position == self.current_position:
                self.toBot(botproto.PositionChanged(
                    position=self.current_position,
                    client_tag=self.target_tag,
                    forced=False))
                self._resetMove()
            else:
                self.current_position.yaw = self.target_position.yaw
                self.current_position.pitch = self.target_position.pitch
                self.current_position.on_ground = self.target_position.on_ground

                d_x = self.target_position.x - self.current_position.x
                d_y = self.target_position.y - self.current_position.y
                d_z = self.target_position.z - self.current_position.z
                distance = math.sqrt(d_x*d_x + d_y*d_y + d_z*d_z)
                if distance == 0:
                    ratio = 0
                else:
                    ratio = min(1.0, self.max_move_per_tick / distance)

                self.current_position.x += ratio * d_x
                self.current_position.y += ratio * d_y
                self.current_position.z += ratio * d_z
                self.current_position.stance += ratio * d_y

        msg = {'msgtype': packets.PLAYERPOSITIONLOOK}
        msg.update(self.current_position.toMessage())
        self.toMinecraft(msg)

        if self.delayed_call:
            self.delayed_call.reset()
        else:
            reactor.callLater(self.tick, self._backgroundUpdate)

    def setBlock(self, msg):
        """Bot SetBlock message processing.

        It doesn't try to be subtile here; it just replace the block under the
        bot with the current tool or the specified block.
        """
        mcmsg = {
                'msgtype': packets.PLAYERBLOCKDIG,
                'status': 0,
                'x': msg.x,
                'y': msg.y+1,  # top face?
                'z': msg.z,
                'face': 1,  # +Y
        }
        self.toMinecraft(mcmsg)
        mcmsg['status'] = 2
        self.toMinecraft(mcmsg)

        tool = dict(self.active_tool)
        if msg.item_id:
            tool['item_id'] = msg.item_id
            tool['uses'] = msg.item_uses
        mcmsg = {
                'msgtype': packets.PLAYERBLOCKPLACE,
                'x': msg.x,
                'y': msg.y,
                'z': msg.z,
                'dir': 1,  # +Y
                'details': tool,
        }
        self.toMinecraft(mcmsg)
        self.toBot(botproto.Ack(client_tag=msg.client_tag))
