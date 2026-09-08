import math
import time


class ChapterLogoSequence:
    """
    First-pass Python equivalent of PROCESS_LOGO for startup use.

    The state transitions follow the recovered GameMaker structure:
        distorted assembly -> stable hold -> outward/fading breakup -> menu

    This first version uses Canvas text as a stand-in for the real logo
    sprites. When the logo assets are wired in, game.py does not need to
    change.
    """

    TAG = "chapter_logo"

    ASSEMBLE_TIME = 1.6
    HOLD_TIME = 2.0
    BREAKUP_TIME = 1.8
    SKIP_TIME = 0.4

    def __init__(self, game, chapter=6, on_complete=None):
        self.game = game
        self.canvas = game.canvas
        self.chapter = chapter
        self.on_complete = on_complete

        self.active = False
        self.finished = False
        self.started_at = 0.0
        self.skipping = False
        self.skip_started_at = 0.0

        self.background = self.canvas.create_rectangle(
            0, 0, 0, 0,
            fill="black",
            outline="",
            state="hidden",
            tags=(self.TAG,)
        )

        self.logo_items = []
        self.chapter_items = []

        for _ in range(3):
            self.logo_items.append(
                self.canvas.create_text(
                    0, 0,
                    text="DELTARUNE",
                    fill="white",
                    anchor="center",
                    state="hidden",
                    tags=(self.TAG,)
                )
            )
            self.chapter_items.append(
                self.canvas.create_text(
                    0, 0,
                    text=f"CHAPTER {self.chapter}",
                    fill="white",
                    anchor="center",
                    state="hidden",
                    tags=(self.TAG,)
                )
            )

        self.heart = self.canvas.create_text(
            0, 0,
            text="♥",
            fill="#ff0000",
            anchor="center",
            state="hidden",
            tags=(self.TAG,)
        )

    def start(self):
        self.active = True
        self.finished = False
        self.started_at = time.perf_counter()
        self.skipping = False
        self.skip_started_at = 0.0

        try:
            self.game.audio.stop_music()
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
        # This class is currently used only for the startup version of
        # PROCESS_LOGO (global.plot == 0), which is skippable in the GML.
        if self.active and key == "z" and not self.skipping:
            self.skipping = True
            self.skip_started_at = time.perf_counter()

    def update(self):
        if not self.active:
            return

        now = time.perf_counter()

        if self.skipping:
            if now - self.skip_started_at >= self.SKIP_TIME:
                self.finish()
            return

        total = (
            self.ASSEMBLE_TIME
            + self.HOLD_TIME
            + self.BREAKUP_TIME
        )

        if now - self.started_at >= total:
            self.finish()

    @staticmethod
    def _fade_hex(base_rgb, alpha):
        alpha = max(0.0, min(1.0, alpha))
        r, g, b = base_rgb
        return (
            f"#{round(r * alpha):02x}"
            f"{round(g * alpha):02x}"
            f"{round(b * alpha):02x}"
        )

    def render(self):
        if not self.active:
            return

        x1, y1 = self.game.ui_to_screen(0, 0)
        x2, y2 = self.game.ui_to_screen(
            self.game.viewport_width,
            self.game.viewport_height
        )
        self.canvas.coords(self.background, x1, y1, x2, y2)

        center_x, logo_y = self.game.ui_to_screen(160, 103)
        _, chapter_y = self.game.ui_to_screen(160, 145)
        _, heart_y = self.game.ui_to_screen(160, 121)

        logo_size = max(1, round(28 * self.game.scale))
        chapter_size = max(1, round(12 * self.game.scale))
        heart_size = max(1, round(15 * self.game.scale))

        elapsed = time.perf_counter() - self.started_at

        if self.skipping:
            phase = "breakup"
            progress = min(
                (time.perf_counter() - self.skip_started_at)
                / self.SKIP_TIME,
                1.0
            )
            spread = 18 * progress * self.game.scale
            alpha = 1.0 - progress

        elif elapsed < self.ASSEMBLE_TIME:
            phase = "assemble"
            progress = elapsed / self.ASSEMBLE_TIME
            factor = 1.0 - progress
            spread = 20 * factor * self.game.scale
            alpha = max(0.15, progress)

        elif elapsed < self.ASSEMBLE_TIME + self.HOLD_TIME:
            phase = "hold"
            spread = 0.0
            alpha = 1.0

        else:
            phase = "breakup"
            breakup_elapsed = (
                elapsed
                - self.ASSEMBLE_TIME
                - self.HOLD_TIME
            )
            progress = min(
                breakup_elapsed / self.BREAKUP_TIME,
                1.0
            )
            spread = 24 * progress * self.game.scale
            alpha = 1.0 - progress

        white = self._fade_hex((255, 255, 255), alpha)
        red = self._fade_hex((255, 0, 0), alpha)

        for i, (logo, chapter) in enumerate(
            zip(self.logo_items, self.chapter_items)
        ):
            if phase == "assemble":
                wave = math.sin(
                    elapsed * 8.0 + i * 0.9
                )
                offset = wave * spread
            elif phase == "breakup":
                offset = (i - 1) * spread
            else:
                offset = 0.0

            self.canvas.coords(
                logo,
                center_x + offset,
                logo_y
            )
            self.canvas.coords(
                chapter,
                center_x - offset,
                chapter_y
            )

            self.canvas.itemconfigure(
                logo,
                fill=white,
                font=("Arial", logo_size, "bold")
            )
            self.canvas.itemconfigure(
                chapter,
                fill=white,
                font=("Arial", chapter_size, "bold")
            )

        self.canvas.coords(self.heart, center_x, heart_y)
        self.canvas.itemconfigure(
            self.heart,
            fill=red,
            font=("Arial", heart_size, "bold")
        )

        self.canvas.tag_raise(self.TAG)

    def finish(self):
        if self.finished:
            return

        self.finished = True
        self.active = False
        self.hide()

        if self.on_complete is not None:
            self.on_complete()
