import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from chapterselect import ChapterSelect

def main():
    chapter_select = ChapterSelect()
    chapter_select.run()

if __name__ == "__main__":
    main()