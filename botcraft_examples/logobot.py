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


"""Minecraft logo bot.

This bot will follow any instruction looking like logo given on the chat line.
Examples:
    - FD 3   Advance by 3 blocks
    - LT 90  Turn by 90 degrees to the left
    - REPEAT 45 [ FD 1 ; LT 8 ]   Draw a circle

See the code for an exhaustive list of functions.
It probably requires flat landscape to work in practice.
"""


import logging
import re
import signal
import sys
import threading
import math
from optparse import OptionParser
import time

from twisted.internet import reactor, protocol, defer

from botcraft import builtinbot
from botcraft import botproto

import logolang


logger = logging.getLogger(__name__)


class Bot(builtinbot.Bot):
    def __init__(self):
        super(Bot, self).__init__()

        self.position = None
        self.current_cmd = None
        self.logo = logolang.Logo()

        self.pen = True
        self.pen_item_id = 0x04
        self.pen_item_uses = 0

    def onServerJoined(self, msg):
        # Center bot on the block.
        target = botproto.Position(self.position)
        target.x = math.floor(target.x) + 0.5
        target.z = math.floor(target.z) + 0.5

        oldy = target.y
        target.y = math.floor(oldy)
        target.stance -= oldy - target.y

        defer.DeferredList([
            self.moveTo(target),
            self.setPenDetails()]).addCallback(self.setupDone)

    def setupDone(self, msgs):
        self.setState(self.stateRunning)

    def stateRunning(self, msg):
        if isinstance(msg, botproto.ChatMessage):
            cmd = msg.text
            self.logo.parse(cmd)
            logging.info('Received new command: %s', cmd)
            if not self.current_cmd:
                self.sendContinue()

    def setPenDetails(self):
        return self.send(botproto.SetActiveTool(
            item_id=self.pen_item_id,
            item_uses=self.pen_item_uses))

    def moveTo(self, target=None, x=None, y=None, z=None, yaw=None, pitch=None):
        target = botproto.Position(target or self.position)
        target.x += x or 0
        target.y += y or 0
        target.stance += y or 0
        target.z += z or 0
        target.yaw += yaw or 0
        target.pitch += pitch or 0
        return self.send(botproto.Move(target=target))

    def _continueMove(self, msg, distance, fullmove_deferred):
        if msg and msg.forced:
            reactor.callLater(0, fullmove_deferred.callback, False)
            return

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

        yaw = self.position.yaw * math.pi / 180

        position = botproto.Position(self.position)
        position.x += -math.sin(yaw) * distance
        position.z += math.cos(yaw) * distance

        d = self.moveTo(position)
        d.addCallback(self._continueMove, remaining, fullmove_deferred)

    def startMove(self, distance):
        d = defer.Deferred()
        self._continueMove(None, distance, d)
        return d

    def draw(self):
        if not self.pen:
            return

        self.send(botproto.SetBlock(
            x=int(self.position.x),
            y=min(127, max(0, int(self.position.y)-2)),
            z=int(self.position.z)))

    def sendContinue(self, success=True):
        """Asynchronously trigger a _continue call."""

        logging.info('sendContinue')
        self.current_cmd = None
        reactor.callLater(0, self._continue)

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
            self.startMove(cmd.value or 1).addCallback(self.sendContinue)
        elif cmd.name == logolang.BACK:
            self.startMove(-cmd.value or -1).addCallback(self.sendContinue)
        elif cmd.name == logolang.PENDOWN:
            self.pen = True
            self.draw()
            self.sendContinue()
        elif cmd.name == logolang.PENUP:
            self.pen = False
            self.sendContinue()
        elif cmd.name == logolang.SETPEN:
            self.pen_item_id = cmd.value1
            self.pen_item_uses = cmd.value2
            self.setPenDetails()
            self.draw()
            self.sendContinue()
        elif cmd.name == logolang.UP:
            self.moveTo(y=1).addCallback(self.sendContinue)
        elif cmd.name == logolang.DOWN:
            self.moveTo(y=-1).addCallback(self.sendContinue)


def main():
    Bot().main()


if __name__ == '__main__':
    main()
