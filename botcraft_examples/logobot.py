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
from optparse import OptionParser
import time

from twisted.internet import reactor, protocol, defer
from twisted.python import log


import botcraft

import logolang


logger = logging.getLogger(__name__)


class LogoBot(botcraft.botbase.MCBot):
    def serverJoined(self):
        self.current_cmd = None
        self.logo = logolang.Logo()

        self.pen = True
        self.pen_details = {
                'item_id': 0x04,
                'count': 1,
                'uses': 0,
        }
        self.setPenDetails()

        # Center bot on the block.
        target = botcraft.botbase.Position(self.current_position)
        target.x = math.floor(target.x) + 0.5
        target.z = math.floor(target.z) + 0.5

        oldy = target.y
        target.y = math.floor(oldy)
        target.stance -= oldy - target.y

        self.moveTo(target)

    def _continueMove(self, success, distance, fullmove_deferred):
        if not success:
            reactor.callLater(0, fullmove_deferred.callback, False)
            return

    def doMove(self, target=None, x=None, y=None, z=None, yaw=None, pitch=None):
        self.draw()
        if not distance:
            reactor.callLater(0, fullmove_deferred.callback, True)
            return

        if distance > 1:
            remaining = distance - 1
            distance = 1
        elif distance < -1:
            remaining = distance + 1
            distance = -1
        else:
            remaining = 0

        yaw = self.current_position.yaw * math.pi / 180

        position = botcraft.botbase.Position(self.current_position)
        position.x += -math.sin(yaw) * distance
        position.z += math.cos(yaw) * distance

        d = self.moveTo(position)
        d.addCallback(self._continueMove, remaining, fullmove_deferred)

    def move(self, distance):
        d = defer.Deferred()
        self._continueMove(True, distance, d)
        return d

    def setPenDetails(self):
        msg = {
                'msgtype': botcraft.packets.CREATIVEACTION,
                'slot': 36,
                'details': self.pen_details,
        }
        self.sendMessage(msg)

    def draw(self):
        if not self.pen:
            return

        msg = {
                'msgtype': botcraft.packets.PLAYERBLOCKDIG,
                'status': 0,
                'x': int(self.current_position.x),
                'y': min(127, max(0, int(self.current_position.y)-1)),
                'z': int(self.current_position.z),
                'face': 1,  # +Y
        }
        self.sendMessage(msg)
        msg['status'] = 2
        self.sendMessage(msg)

        msg = {
                'msgtype': botcraft.packets.PLAYERBLOCKPLACE,
                'x': int(self.current_position.x),
                'y': min(127, max(0, int(self.current_position.y)-2)),
                'z': int(self.current_position.z),
                'dir': 1,  # +Y
                'details': self.pen_details,
        }
        self.sendMessage(msg)

    def chatReceived(self, message):
        m = re.search('^<[^>]+> (.*)$', message)
        if not m:
            logger.info('Chat message: %s', message)
            return
        cmd = m.group(1)
        self.logo.parse(cmd)
        logging.info('Received new command: %s', cmd)
        if not self.current_cmd:
            self.sendContinue()

    def sendContinue(self, success=True):
        logging.info('sendContinue')
        self.current_cmd = None
        reactor.callFromThread(self._continue)

    def _continue(self):
        logging.info('_continue')
        if self.current_cmd:
            return

        try:
            cmd = self.logo.next()
        except StopIteration:
            logging.info('No remaining commands')
            return

        self.current_cmd = cmd

        logging.info('Executing command %s', self.current_cmd)

        if cmd.name == logolang.LEFT:
            self.moveTo(yaw=-cmd.value).addCallback(self.sendContinue)
        elif cmd.name == logolang.RIGHT:
            self.moveTo(yaw=cmd.value).addCallback(self.sendContinue)
        elif cmd.name == logolang.FORWARD:
            self.move(cmd.value or 1).addCallback(self.sendContinue)
        elif cmd.name == logolang.BACK:
            self.move(-cmd.value or -1).addCallback(self.sendContinue)
        elif cmd.name == logolang.PENDOWN:
            self.pen = True
            self.draw()
            self.sendContinue()
        elif cmd.name == logolang.PENUP:
            self.pen = False
            self.sendContinue()
        elif cmd.name == logolang.SETPEN:
            self.pen_details['item_id'] = cmd.value1
            self.pen_details['uses'] = cmd.value2
            self.setPenDetails()
            self.draw()
            self.sendContinue()
        elif cmd.name == logolang.UP:
            self.moveTo(y=1).addCallback(self.sendContinue)
        elif cmd.name == logolang.DOWN:
            self.moveTo(y=-1).addCallback(self.sendContinue)


def main():
    botcraft.main(LogoBot())

if __name__ == '__main__':
    main()
