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

from twisted.internet import reactor
from twisted.python import log

from . import util
from . import messages
from . import parsing
from . import packets


logger = logging.getLogger(__name__)


class Bot(object):
    def __init__(self, mcproto):
        self.mcproto = mcproto
        self.current_position = None

    def doMove(self, target=None, x=None, y=None, z=None, yaw=None, pitch=None):
        target = target or Position(self.current_position)
        target.x += x or 0
        target.y += y or 0
        target.z += z or 0
        target.stance += y or 0
        target.yaw += yaw or 0
        target.pitch += pitch or 0

        self.mcproto.doMove(target)

    def onMoved(self, position):
        """Called everytime the position of the bot is changed."""
        pass

    def onServerJoined(self):
        """Bot is connected to server, ready to take orders."""
        pass
