from botcraft import builtinbot
from botcraft import botproto


class Bot(builtinbot.Bot):
    def onChatMessage(self, msg):
        if msg.username != self.username:
            self.send(botproto.Say(text=msg.text)).addCallback(self._dump, msg.text)

    def _dump(self, msg, text):
        print 'I just said %r' % text


def main():
    Bot().main()


if __name__ == '__main__':
    main()
