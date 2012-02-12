from botcraft import builtinbot


class Bot(builtinbot.Bot):
    def onChatMessage(self, msg):
        print 'Received message from %r: %r' % (msg.username, msg.text)


def main():
    Bot().main()


if __name__ == '__main__':
    main()
