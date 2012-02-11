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

import logging
import re
import signal
import sys
import threading
import math
import time

from twisted.internet import reactor, protocol, defer
from twisted.python import log

from . import util
from . import messages
from . import parsing
from . import packets


logger = logging.getLogger(__name__)


class MCProtocol(protocol.Protocol):
    def connectionMade(self):
        logger.debug('Protocol connectionMade.')

        self.protocol_id = 23
        self.send_spec = messages.protocol[self.protocol_id][0]
        self.receive_spec = messages.protocol[self.protocol_id][1]
        self.stream = util.Stream()

    def sendMessage(self, msg):
        msgtype = msg['msgtype']
        msg_emitter = self.send_spec[msgtype]
        s = msg_emitter.emit(msg)
        #logger.debug("Sending message (size %i): %s = %r", len(s), msg, s)
        self.transport.write(s)

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
        except util.PartialPacketException:
            return None

    def dataReceived(self, data):
        self.stream.append(data)

        msg = self._parsePacket()
        while msg:
            # Do something
            self.messageReceived(msg)
            msg = self._parsePacket()

    def messageReceived(self, msg):
        pass


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


class MCBot(MCProtocol):
    def connectionMade(self):
        MCProtocol.connectionMade(self)

        self.username = 'turtle'
        self.tick = 0.050
        self.max_move_per_tick = 1.0

        self.delayed_call = None
        self.world_time = None

        self.spawn = Spawn()
        self.players = {}

        self.current_position = Position()
        self._resetMoveTo()

        self.initialized = False

        self.sendMessage({'msgtype': packets.HANDSHAKE, 'username': self.username})

    def _resetMoveTo(self):
        self.target_position = None
        self._on_target = None

    def _backgroundUpdate(self):
        if self.target_position:
            if self.target_position == self.current_position:
                reactor.callLater(0, self._on_target.callback, True)
                self._resetMoveTo()
            else:
                self.current_position.yaw = self.target_position.yaw
                self.current_position.pitch = self.target_position.pitch
                self.current_position.on_ground = self.target_position.on_ground

                d_x = self.target_position.x - self.current_position.x
                d_y = self.target_position.y - self.current_position.y
                d_z = self.target_position.z - self.current_position.z
                d = math.sqrt(d_x*d_x + d_y*d_y + d_z*d_z)
                if d == 0:
                    r = 0
                else:
                    r = min(1.0, self.max_move_per_tick / d)

                self.current_position.x += r * d_x
                self.current_position.y += r * d_y
                self.current_position.z += r * d_z
                self.current_position.stance += r * d_y

        msg = {'msgtype': packets.PLAYERPOSITIONLOOK}
        msg.update(self.current_position.toMessage())
        self.sendMessage(msg)

        if self.delayed_call:
            self.delayed_call.reset()
        else:
            reactor.callLater(self.tick, self._backgroundUpdate)

    def messageReceived(self, msg):
        if msg['msgtype'] == packets.KEEPALIVE:
            self.sendMessage({'msgtype': packets.KEEPALIVE, 'id': 0})
        elif msg['msgtype'] == packets.LOGIN:
            pass
        elif msg['msgtype'] == packets.HANDSHAKE:
            logger.debug('Handshake done, hash: %s', msg['hash'])
            self.sendMessage({
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
            new_position = Position()
            new_position.fromMessage(msg)
            if new_position != self.current_position:
                self.current_position = new_position

                if self._on_target:
                    reactor.callLater(0, self._on_target.callback, False)
                self._resetMoveTo()
                self._backgroundUpdate()

            if not self.initialized:
                self.initialized = True
                self.serverJoined()
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

    def chatReceived(self, message):
        logger.info('Chat message: %s', message)

    def sendChat(self, message):
        msg = {
                'msgtype': packets.CHAT,
                'chat_msg': message[:100],
        }
        self.sendMessage(msg)

    def moveTo(self, target=None, x=None, y=None, z=None, yaw=None, pitch=None):
        target = target or Position(self.current_position)
        target.x += x or 0
        target.y += y or 0
        target.z += z or 0
        target.stance += y or 0
        target.yaw += yaw or 0
        target.pitch += pitch or 0
        self.target_position = target
        self._on_target = defer.Deferred()
        return self._on_target

    def serverJoined(self):
        pass


class MCBotFactory(protocol.ReconnectingClientFactory):
    def startedConnecting(self, connector):
        print 'Started to connect.'

    def buildProtocol(self, addr):
        print 'Connected. (resetting reconnection delay)'
        self.resetDelay()
        return self.bot

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                                  reason)
