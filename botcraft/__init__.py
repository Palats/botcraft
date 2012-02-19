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


"""Botcraft, a minecraft bot library."""


import logging
import sys

import gflags
from twisted.internet import reactor

logger = logging.getLogger(__name__)
FLAGS = gflags.FLAGS


gflags.DEFINE_enum('loglevel', 'error', ['debug', 'info', 'warn', 'error'],
                   'Log level.')


class LogHandler(logging.StreamHandler):
    """Generic log handler for all of botcraft.

    This is currently just regular logging. More might be added in the future.
    """
    def emit(self, record):
        super(LogHandler, self).emit(record)


def init():
    """Initialize botcraft library, parsing command line arguments.

    This must be called before doing anything else.
    """
    try:
        unused_argv = FLAGS(sys.argv)  # parse flags
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    handler = LogHandler()
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)
    logging.root.setLevel(FLAGS.loglevel.upper())


def run():
    """Start botcraft."""
    reactor.run()
