import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
from game import Game
def main():
    game = Game()
    game.run()
if __name__ == '__main__':
    main()