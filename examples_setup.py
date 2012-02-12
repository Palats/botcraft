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

from setuptools import setup, find_packages

setup(
    name = 'botcraft-examples',
    description = 'Examples bots using botcraft library',
    version = '0.1',
    author = 'Pierre Palatin',
    author_email = 'pierre@palatin.fr',
    keywords = 'minecraft bot examples',
    url = 'https://github.com/Palats/botcraft',
    license = 'GPLv2',
    entry_points = {
        'console_scripts': [
            'idlebot = botcraft_examples.idlebot:main',
            'logobot = botcraft_examples.logo:main',
        ]
    },
    packages = ['botcraft_examples'],
    install_requires = [
        'botcraft',
        'lepl',     # For the logo bot
    ],
    # test_suite
    # keywords
)
