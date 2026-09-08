import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LEGEND_MUSIC = BASE_DIR / "mus" / "legend_altered.ogg"


class LegendSequence:
    """
    First-pass Python equivalent of obj_legend for the Chapter 6 startup path.

    This version concentrates on the recovered control flow, text phases,
    skip behavior, and Legend -> PROCESS_LOGO handoff. The prophecy artwork
    and shader/scroll effect can be replaced later without changing game.py.
    """

    TAG = "legend_sequence"

    # First-pass timing values in seconds. These are intentionally isolated
    # here so they can be tuned when we do the frame-accurate recreation.
    TEXT_ONCE = 0.20
    TEXT_HOPE_DREAMS = 3.70
    TEXT_LIGHT_DARK = 5.70
    TEXT_DELTA_RUNE = 7.70
    FINISH_TIME = 10.50

    SKIP_READY_TIME = 1.0
    SKIP_FADE_TIME = 0.35

    def __init__(self, game, on_complete=None):
        self.game = game
        self.canvas = game.canvas
        self.on_complete = on_complete

        self.active = False
        self.finished = False
        self.started_at = 0.0

        self.press_count = 0
        self.skipping = False
        self.skip_started_at = 0.0
        self.current_phase = None

        self.background = self.canvas.create_rectangle(
            0, 0, 0, 0,
            fill="black",
            outline="",
            state="hidden",
            tags=(self.TAG,)
        )

        # Temporary stand-in for the chapter-specific prophecy image.
        self.art_placeholder = self.canvas.create_text(
            0, 0,
            text="PROPHECY ART",
            fill="#3f5f8f",
            anchor="center",
            state="hidden",
            tags=(self.TAG,)
        )

        self.left_text = self.canvas.create_text(
            0, 0,
            text="",
            fill="white",
            justify="center",
            anchor="center",
            state="hidden",
            tags=(self.TAG,)
        )

        self.right_text = self.canvas.create_text(
            0, 0,
            text="",
            fill="white",
            justify="center",
            anchor="center",
            state="hidden",
            tags=(self.TAG,)
        )

    def start(self):
        self.active = True
        self.finished = False
        self.started_at = time.perf_counter()
        self.press_count = 0
        self.skipping = False
        self.skip_started_at = 0.0
        self.current_phase = None

        try:
            self.game.audio.stop_music()
        except Exception:
            pass

        if LEGEND_MUSIC.exists():
            try:
                self.game.audio.play_music(str(LEGEND_MUSIC))
            except Exception:
                pass

        self.show()
        self.render()

    def show(self):
        self.canvas.itemconfigure(self.TAG, state="normal")
        self.canvas.tag_raise(self.TAG)

    def hide(self):
        self.canvas.itemconfigure(self.TAG, state="hidden")

    def handle_input(self, key):
        if not self.active or key != "z":
            return

        self.press_count += 1
        elapsed = time.perf_counter() - self.started_at

        # Mirrors the useful part of obj_legend's startup skip rule:
        # one press after the safety period, or two presses at any time.
        if (
            not self.skipping
            and (
                elapsed >= self.SKIP_READY_TIME
                or self.press_count >= 2
            )
        ):
            self.skipping = True
            self.skip_started_at = time.perf_counter()

            self.canvas.itemconfigure(self.left_text, text="")
            self.canvas.itemconfigure(self.right_text, text="")
            self.canvas.itemconfigure(
                self.art_placeholder,
                text=""
            )

            try:
                self.game.audio.stop_music()
            except Exception:
                pass

    def update(self):
        if not self.active:
            return

        now = time.perf_counter()

        if self.skipping:
            if now - self.skip_started_at >= self.SKIP_FADE_TIME:
                self.finish()
            return

        elapsed = now - self.started_at

        if elapsed >= self.FINISH_TIME:
            self.finish()
            return

        self._set_text_phase(elapsed)

    def _set_text_phase(self, elapsed):
        if elapsed < self.TEXT_ONCE:
            phase = "blank"
        elif elapsed < self.TEXT_HOPE_DREAMS:
            phase = "once"
        elif elapsed < self.TEXT_LIGHT_DARK:
            phase = "hope_dreams"
        elif elapsed < self.TEXT_DELTA_RUNE:
            phase = "light_dark"
        else:
            phase = "delta_rune"

        if phase == self.current_phase:
            return

        self.current_phase = phase

        if phase == "blank":
            left = ""
            right = ""
        elif phase == "once":
            left = "Once upon a time, a LEGEND\nwas whispered among shadows."
            right = ""
        elif phase == "hope_dreams":
            left = "It was\na LEGEND\nof HOPE."
            right = "It was\na LEGEND\nof DREAMS."
        elif phase == "light_dark":
            left = "It was\na LEGEND\nof LIGHT."
            right = "It was\na LEGEND\nof DARK."
        else:
            left = "This is the legend of\nDELTA RUNE"
            right = ""

        self.canvas.itemconfigure(self.left_text, text=left)
        self.canvas.itemconfigure(self.right_text, text=right)

    def render(self):
        if not self.active:
            return

        x1, y1 = self.game.ui_to_screen(0, 0)
        x2, y2 = self.game.ui_to_screen(
            self.game.viewport_width,
            self.game.viewport_height
        )

        art_x, art_y = self.game.ui_to_screen(160, 80)
        left_x, text_y = self.game.ui_to_screen(95, 175)
        right_x, _ = self.game.ui_to_screen(225, 175)

        self.canvas.coords(self.background, x1, y1, x2, y2)
        self.canvas.coords(self.art_placeholder, art_x, art_y)
        self.canvas.coords(self.left_text, left_x, text_y)
        self.canvas.coords(self.right_text, right_x, text_y)

        art_size = max(1, round(15 * self.game.scale))
        text_size = max(1, round(9 * self.game.scale))

        self.canvas.itemconfigure(
            self.art_placeholder,
            font=("Arial", art_size, "bold")
        )
        self.canvas.itemconfigure(
            self.left_text,
            font=("Arial", text_size)
        )
        self.canvas.itemconfigure(
            self.right_text,
            font=("Arial", text_size)
        )

        self.canvas.tag_raise(self.TAG)

    def finish(self):
        if self.finished:
            return

        self.finished = True
        self.active = False

        try:
            self.game.audio.stop_music()
        except Exception:
            pass

        self.hide()

        if self.on_complete is not None:
            self.on_complete()
