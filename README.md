Botcraft
========

A library/framework to easily create minecraft bots.


Minecraft world is perfect for AI & bot writing. However, the server protocol is complex, while at the same time allowing clients to cheat with the world rules quite a lot. This library aims to provide an easy or even trivial way to write bots living in a minecraft world.

To that purpose, Botcraft proposes custom bot protocols, with straightforward operations - move to this block, change this block, send this chat message. Those protocols are designed to be language neutral and it should be possible to use botcraft to write bots in other languages too.

Lots of it has been possible to write thanks to http://www.wiki.vg/Protocol and related pages, which provides an extensive documentation of minecraft protocol and formats.

Logo bot example: [basic commands](http://www.youtube.com/watch?v=r0BrpESwJmQ), [drawing a circle](http://www.youtube.com/watch?v=sQlFfoswAkA)


Features
========

 - The base of minecraft protocol is abstracted away so the bot doesn't have to care about things like periodic updates.
 - Basic functions - connection, move to a given coordinate, change active tools, listen on the chat line
 - Full parsing of minecraft protocol (thanks to https://github.com/mmcgill/mc3p) ; not everything is available currently though
 - A few examples; minimal bot is only a few lines long; an example bot follow order in logo syntax.

And hopefully coming:

 - More complate functions available to the bot: state of the blocks, position of items and so on.
 - More bot examples.
 - Support of survival mode.
 - Multiple minecraft protocol support, to support easily new versions.

In the future:

 - Multiple Bot protocol: I want it to be possible to have different bot modes with botcraft. Basically, that would allow to have specialized bots, for specific universe. We can imagine with that to have bot combats in arena, with differnt rules, different type of survival and so on.
 - http protocol; that would enable creation of bots in other languages


Installation
============
There are 2 parts: the botcraft library and the examples. Both can be installed in a python virtualenv (http://pypi.python.org/pypi/virtualenv).


The following command should do most of the trick:

    git clone https://github.com/Palats/botcraft.git
    cd botcraft
    python virtualenv.py env
    source env/bin/activate
    python setup.py install
    python examples_setup.py install

From there, you should be able to start the examples:

    echobot
    logobot [--hostname localhost]
