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
import collections
import Queue

from twisted.internet import reactor, protocol, defer
from twisted.python import log

from . import messages
from . import parsing
from . import packets
from . import botproto


logger = logging.getLogger(__name__)


class MCBotFactory(protocol.ReconnectingClientFactory):
    def startedConnecting(self, connector):
        print 'Started to connect.'

    def buildProtocol(self, addr):
        print 'Connected. (resetting reconnection delay)'
        self.resetDelay()
        return self.onBuildProtocol()

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                                  reason)

    def onBuildProtocol(self):
        pass


class MCProtocol(protocol.Protocol):
    def connectionMade(self):
        logger.debug('Protocol connectionMade.')

        self.protocol_id = 23
        self.send_spec = messages.protocol[self.protocol_id][0]
        self.receive_spec = messages.protocol[self.protocol_id][1]
        self.stream = parsing.Stream()

        self.onConnected()

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
        except parsing.PartialPacketException:
            return None

    def dataReceived(self, data):
        self.stream.append(data)

        msg = self._parsePacket()
        while msg:
            self.onMessage(msg)
            msg = self._parsePacket()

    def onConnected(self):
        pass

    def onMessage(self, msg):
        pass


class MCBot(object):
    def __init__(self):
        self.username = None   # Overridden by the connect message
        self.tick = 0.050
        self.max_move_per_tick = 1.0

        self.delayed_call = None
        self.world_time = None

        self.spawn = botproto.Spawn()
        self.players = {}

        self.current_position = botproto.Position()
        self.active_tool = {
                'item_id': 0x1,
                'count': 1,
                'uses': 0
        }
        self._resetMove()

        self.initialized = False

        self.factory = MCBotFactory()
        self.factory.onBuildProtocol = self.onBuildProtocol
        self.protocol = None

        self.connect_callback = None
        self.chat_callbacks = collections.defaultdict(Queue.Queue)

    def connect(self, host, port):
        reactor.connectTCP(host, port, self.factory)

    def onBuildProtocol(self):
        self.protocol = MCProtocol()
        self.protocol.onConnected = self.onConnected
        self.protocol.onMessage = self.fromMinecraft
        return self.protocol

    def onConnected(self):
        self.toMinecraft({'msgtype': packets.HANDSHAKE, 'username': self.username})

    def toMinecraft(self, msg):
        self.protocol.sendMessage(msg)

    def fromMinecraft(self, msg):
        """Message received from minecraft server."""

        if msg['msgtype'] == packets.KEEPALIVE:
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
                self.notifyPosition()
                if self._on_target:
                    reactor.callLater(0, self._on_target.callback, False)
                self._resetMove()
                self._backgroundUpdate()

            if not self.initialized:
                self.initialized = True
                self._toBot(botproto.ServerJoined())
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

    def _toBot(self, msg):
        reactor.callLater(0, self.toBot, msg)

    def toBot(self, msg):
        pass

    def fromBot(self, msg):
        callback = defer.Deferred()
        reactor.callLater(0, self.dispatchFromBot, msg, callback)
        return callback

    def dispatchFromBot(self, msg, callback):
        if isinstance(msg, botproto.Connect):
            self.username = msg.username or self.username
            hostname = msg.hostname
            port = msg.port or None
            self.connect(hostname, port)
            self.connect_callback = callback
        elif isinstance(msg, botproto.Say):
            if len(msg.text) > 100:
                callback.errback()
            else:
                text = msg.text[:100]
                self.chat_callbacks[text].put(callback)
                msg = {'msgtype': packets.CHAT,
                       'chat_msg': msg.text[:100]}
                self.toMinecraft(msg)
        elif isinstance(msg, botproto.Move):
            self._resetMove()
            self.target_position = msg.target
            self._on_target = callback
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
            callback.callback(None)
        elif isinstance(msg, botproto.SetBlock):
            self.setBlock(msg)

    def chatReceived(self, message):
        logger.info('Chat message: %s', message)
        m = re.search('^<([^>]+)> (.*)$', message)
        if not m:
            logger.warning('Unknown chat message: %s', message)
            return
        username = m.group(1)
        text = m.group(2)

        if username == self.username and text in self.chat_callbacks:
            callback = self.chat_callbacks[text].get(False)
            if callback:
                callback.callback(None)

            if self.chat_callbacks[text].empty():
                # Remove empty queues so they don't accumulate for everything
                # that is said on chat. Checking empty() on a queue is not
                # thread proof, but given that we're using twisted here, and so
                # are not executing in parallel, we should be fine.
                del self.chat_callbacks[text]

        self._toBot(botproto.ChatMessage(username=username, text=text))

    def _resetMove(self):
        self.target_position = None
        self._on_target = None

    def notifyPosition(self):
        self._toBot(botproto.PositionChanged(position=self.current_position))

    def _backgroundUpdate(self):
        self.notifyPosition()
        if self.target_position:
            if self.target_position == self.current_position:
                reactor.callLater(0, self._on_target.callback, True)
                self._resetMove()
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
        self.toMinecraft(msg)

        if self.delayed_call:
            self.delayed_call.reset()
        else:
            reactor.callLater(self.tick, self._backgroundUpdate)

    def setBlock(self, msg):
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
            tool['item_id'] = mcmsg.item_id
            tool['uses'] = mcmsg.item_uses
        mcmsg = {
                'msgtype': packets.PLAYERBLOCKPLACE,
                'x': msg.x,
                'y': msg.y,
                'z': msg.z,
                'dir': 1,  # +Y
                'details': tool,
        }
        self.toMinecraft(mcmsg)
