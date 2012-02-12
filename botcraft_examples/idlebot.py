from botcraft import builtinbot


class Bot(builtinbot.Bot):
    DEFAULT_NAME = 'idlebot'


def main():
    Bot().main()


if __name__ == '__main__':
    main()
