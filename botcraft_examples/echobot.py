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


"""A simple echo minecraft bot.

The bot connects and does not nothing beside repeating everything people say on
the chat line.
"""


from botcraft import builtinbot
from botcraft import botproto


class Bot(builtinbot.Bot):
    """Echo bot implementation."""
    def onChatMessage(self, msg):
        """Triggers when a chat message is sent, even our own."""
        if msg.username != self.username:
            self.send(botproto.Say(text=msg.text)).addCallback(self._dump)

    def _dump(self, msg):
        print 'I just said %r' % msg.text


def main():
    """Script entry point."""
    Bot().main()


if __name__ == '__main__':
    main()
