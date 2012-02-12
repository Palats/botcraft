from botcraft import builtinbot
from botcraft import botproto


class Bot(builtinbot.Bot):
    def onChatMessage(self, msg):
        if msg.username != self.username:
            self.toServer(botproto.Say(text=msg.text))


def main():
    Bot().main()


if __name__ == '__main__':
    main()
