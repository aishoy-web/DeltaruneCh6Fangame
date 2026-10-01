import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from chapterselect import ChapterSelect
# from game import Game #for testing, just change the reference to the game class

def main():
    chapter_select = ChapterSelect()
    chapter_select.run()

if __name__ == "__main__":
    main()

"""
Official Statements from Toby Fox:
With Chapter 5, we completed the last of the necessary setup for Chapter 6 and 7.
From Chapter 6 onward, there are no more wacky silly adventures, 
and you will begin to see the results of the setup that has been made so far.
Chapter 6 is a shorter, straightforward chapter that focuses on one aspect of the story.
Because of that, many things are still not touched on here – in fact, it may surprise you what was missing!
But one thing will be clarified, whether you’re ready or not.
Some of you may say “Wait! You need to make the chapters longer, not shorter!” 
That’s an extremely reasonable concern, but... 
by the end of Chapter 7 I’m 100% sure you’ll understand why I feel confident about the way I’m telling this story. 
Don’t worry about the pacing until it’s over!

Barring any major restructuring, the main things that will continue to need development time are
the boss of the chapter and polishing cutscenes.

However, I do think it’s important to mention, sometimes you don’t have all the information, 
or I had a different expectation about how certain info would be interpreted or combined.

By the way, I told Fangamer not to expect to make too much merchandise for Chapter 6 and 7.

Anyway, there aren’t any more Chapters where we focus on goofy, 
attention-hungry Darkner characters with the potential to win weird popularity contests.
"""