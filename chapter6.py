import argparse
from pathlib import Path

from game import Game


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--ready-file",
        default=None,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # KEEP whatever startup logic you already had here.
    startup = None  # replace with your existing startup assignment

    # Only hide the window when Chapter Select launched us.
    launched_from_chapter_select = args.ready_file is not None

    game = Game(
        startup,
        start_hidden=launched_from_chapter_select,
    )

    if launched_from_chapter_select:
        # Finish setting up/showing Chapter 6 first.
        game.show_window()

        # Only now tell Chapter Select that it can destroy
        # its black fullscreen loading curtain.
        Path(args.ready_file).write_text(
            "ready",
            encoding="utf-8",
        )

    game.run()


if __name__ == "__main__":
    main()