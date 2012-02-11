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
import optparse

from twisted.internet import reactor

from . import botbase


logger = logging.getLogger(__name__)


def parse_args():
    """Return host and port, or print usage and exit."""
    usage = "usage: %prog [options] host [port]"
    desc = """Minecraft bot"""
    parser = optparse.OptionParser(usage=usage,
                                   description=desc)
    parser.add_option("-l", "--log-level", dest="loglvl", metavar="LEVEL",
                      choices=["debug","info","warn","error"],
                      help="Override logging.conf root log level")
    parser.add_option("--log-file", dest='logfile', metavar="FILE", default=None,
                      help="logging configuration file (optional)")
    (opts,args) = parser.parse_args()

    if not 1 <= len(args) <= 2:
        parser.error("Incorrect number of arguments.") # Calls sys.exit()

    host = args[0]
    port = 25565
    if len(args) > 1:
        try:
            port = int(args[1])
        except ValueError:
            parser.error("Invalid port %s" % args[1])

    if len(args) == 2:
        try:
            port = int(sys.argv[2])
        except:
            parser.error("Invalid port '%s'" % args[1])

    return (host, port, opts)


class LogHandler(logging.StreamHandler):
    def emit(self, record):
        super(LogHandler, self).emit(record)


def main(bot):
    ch = LogHandler()
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    (host, port, opts) = parse_args()

    if opts.logfile:
        util.config_logging(opts.logfile)

    if opts.loglvl:
        logger.root.setLevel(getattr(logging, opts.loglvl.upper()))

    factory = botbase.MCBotFactory()
    factory.bot = bot
    bot.factory = factory
    reactor.connectTCP(host, port, factory)

    reactor.run()
