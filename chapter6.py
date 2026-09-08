import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from startup import resolve_startup
from game import Game


def main():

    startup = resolve_startup()

    game = Game(startup)
    game.run()


if __name__ == "__main__":
    main()