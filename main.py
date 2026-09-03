import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from chapterselect import ChapterSelect
from game import Game #for testing, just change the reference to the game class

def main():
    chapter_select = ChapterSelect()
    chapter_select.run()

if __name__ == "__main__":
    main()