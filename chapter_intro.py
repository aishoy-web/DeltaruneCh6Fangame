import math
import random
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk


BASE_DIR = Path(__file__).resolve().parent
INTRO_DIR = BASE_DIR / "sprites" / "intro"


@dataclass
class AmbientFlake:
    x: float
    y: float
    vy: float
    vx: float
    size: int
    phase: float


@dataclass
class LogoFlake:
    x: float
    y: float
    target_x: int
    target_y: int
    vx: float
    start_time: float
    fall_speed: float
    drift_phase: float
    drift_amount: float
    size: int
    settled: bool = False


class ChapterIntro:
    """Chapter 6 first-time intro.

    Sequence:
        black screen + IMAGE_LOGO_CENTER_HEART
        -> snow begins falling
        -> selected flakes settle into the shape of IMAGE_LOGO
        -> the settled snow itself is the completed logo
        -> completed snow-logo holds briefly
        -> fade to black
        -> game.py reveals File Select underneath black and fades it in

    The animation is rendered at DELTARUNE's 320x240 logical resolution and
    then nearest-neighbour scaled by Game, so the particles stay pixel crisp.
    """

    TAG = "chapter_intro"
    FRAME_MS = 33

    # --------------------------------------------------
    # Layout
    # --------------------------------------------------
    LOGO_CENTER_X = 160
    LOGO_CENTER_Y = 110
    HEART_CENTER_X = 155
    HEART_CENTER_Y = 114

    # These are deliberately easy to tune after seeing the animation in-game.
    LOGO_SCALE = 1.0
    HEART_SCALE = 1.0

    # --------------------------------------------------
    # Timing (seconds)
    # --------------------------------------------------
    SNOW_START = 0.5
    LOGO_SNOW_START = 2.25

    # Approximately this many logo-forming flakes enter per second.
    LOGO_FLAKES_PER_SECOND = 60.0

    # Timing after the LAST logo flake has landed.
    LOGO_HOLD_TIME = 1.50
    FADE_TO_BLACK_TIME = 0.5

    # Z cannot skip on the very first frames.
    SKIP_SAFETY = 0.35
    SKIP_FADE_TIME = 0.45

    # --------------------------------------------------
    # Snow tuning
    # --------------------------------------------------
    # Every visible snow particle uses exactly this size.
    SNOW_PARTICLE_SIZE = 2

    AMBIENT_FLAKES_PER_SECOND = 8.0
    AMBIENT_SPEED_MIN = 22.0
    AMBIENT_SPEED_MAX = 48.0
    AMBIENT_DRIFT_MAX = 10.0

    # Logo-forming flakes use the SAME vertical speed range as ambient snow.
    # Keeping only a separate drift amount lets us tune their final approach
    # without making their falling speed give them away.
    # TARGET_DRIFT_MAX = 2.5

    # One target flake for roughly every STEP x STEP visible logo block.
    # 1 = very dense, 2 = default, 3+ = increasingly sparse.
    LOGO_SAMPLE_STEP = 2

    def __init__(self, game, on_complete=None):
        self.game = game
        self.canvas = game.canvas
        self.on_complete = on_complete

        self.active = False
        self.finished = False
        self.started_at = 0.0
        self.last_update_at = 0.0

        self.skip_started_at = None
        self.ambient_spawn_accumulator = 0.0

        self.ambient_flakes = []
        self.logo_flakes = []
        self.pending_logo_flakes = []
        self.logo_complete_at = self.LOGO_SNOW_START

        self.logo_pil = None
        self.heart_pil = None
        self.logo_x = 0
        self.logo_y = 0
        self.heart_x = 0
        self.heart_y = 0

        self.settled_logo = Image.new(
            "RGBA",
            (self.game.viewport_width, self.game.viewport_height),
            (0, 0, 0, 0),
        )

        # Full-canvas black rectangle keeps the widescreen/letterbox region
        # black even though the animation itself is only 320x240.
        self.black_background = self.canvas.create_rectangle(
            0, 0, 0, 0,
            fill="black",
            outline="",
            state="hidden",
            tags=(self.TAG,),
        )

        self.frame_item = self.canvas.create_image(
            0, 0,
            anchor="nw",
            state="hidden",
            tags=(self.TAG,),
        )
        self.frame_photo = None

        self._load_assets()
        self._build_logo_flake_schedule()

    # ==================================================
    # Asset loading
    # ==================================================

    @staticmethod
    def _find_asset(stem):
        if not INTRO_DIR.exists():
            raise FileNotFoundError(
                f"Chapter intro asset folder does not exist: {INTRO_DIR}"
            )

        stem_cf = stem.casefold()
        exact = []
        prefixed = []

        for path in INTRO_DIR.iterdir():
            if not path.is_file():
                continue

            if path.stem.casefold() == stem_cf:
                exact.append(path)
            elif path.stem.casefold().startswith(stem_cf + "_"):
                prefixed.append(path)

        matches = exact or prefixed
        if not matches:
            raise FileNotFoundError(
                f"Could not find {stem} in {INTRO_DIR}. "
                f"Expected a file such as {stem}.png"
            )

        return sorted(matches)[0]

    @staticmethod
    def _scaled_asset(image, scale):
        if scale == 1.0:
            return image

        width = max(1, round(image.width * scale))
        height = max(1, round(image.height * scale))
        return image.resize((width, height), Image.Resampling.NEAREST)

    def _load_assets(self):
        logo_path = self._find_asset("IMAGE_LOGO")
        heart_path = self._find_asset("IMAGE_LOGO_CENTER_HEART")

        self.logo_pil = Image.open(logo_path).convert("RGBA")
        self.heart_pil = Image.open(heart_path).convert("RGBA")

        self.logo_pil = self._scaled_asset(self.logo_pil, self.LOGO_SCALE)
        self.heart_pil = self._scaled_asset(self.heart_pil, self.HEART_SCALE)

        self.logo_x = round(self.LOGO_CENTER_X - self.logo_pil.width / 2)
        self.logo_y = round(self.LOGO_CENTER_Y - self.logo_pil.height / 2)
        self.heart_x = round(self.HEART_CENTER_X - self.heart_pil.width / 2)
        self.heart_y = round(self.HEART_CENTER_Y - self.heart_pil.height / 2)

    # ==================================================
    # Snow setup
    # ==================================================

    @staticmethod
    def _is_logo_pixel(pixel):
        r, g, b, a = pixel
        if a < 48:
            return False

        # Avoid treating an opaque black sprite background as part of the
        # logo. Actual white/bright logo pixels remain valid.
        return max(r, g, b) >= 80

    def _build_logo_flake_schedule(self):
        self.pending_logo_flakes.clear()

        pixels = self.logo_pil.load()
        step = max(1, int(self.LOGO_SAMPLE_STEP))
        targets = []

        for sy in range(0, self.logo_pil.height, step):
            for sx in range(0, self.logo_pil.width, step):
                found_visible = False

                # For STEP > 1, preserve thin parts of the logo if *any*
                # pixel inside this block is visible.
                for oy in range(step):
                    py = sy + oy
                    if py >= self.logo_pil.height:
                        break

                    for ox in range(step):
                        px = sx + ox
                        if px >= self.logo_pil.width:
                            break

                        if self._is_logo_pixel(pixels[px, py]):
                            found_visible = True
                            break

                    if found_visible:
                        break

                if found_visible:
                    targets.append((self.logo_x + sx, self.logo_y + sy))

        random.shuffle(targets)

        target_count = len(targets)

        # Reset this every time the schedule is rebuilt.
        self.logo_complete_at = self.LOGO_SNOW_START

        flake_interval = 1.0 / self.LOGO_FLAKES_PER_SECOND

        for index, (target_x, target_y) in enumerate(targets):
            # Same spawn height as ordinary snow.
            start_y = random.uniform(-12, -1)

            # Same vertical speed range as ordinary snow.
            speed = random.uniform(
                self.AMBIENT_SPEED_MIN,
                self.AMBIENT_SPEED_MAX,
            )

            distance = max(1.0, target_y - start_y)
            travel_time = distance / max(speed, 1.0)

            # Same random horizontal velocity range as ordinary snow.
            vx = random.uniform(
                -self.AMBIENT_DRIFT_MAX,
                self.AMBIENT_DRIFT_MAX,
            )

            # Exactly ~8 target flakes per second.
            start_time = (
                self.LOGO_SNOW_START
                + index * flake_interval
            )

            # Small timing variation keeps the snowfall from looking clockwork.
            # Keep this much smaller than flake_interval so it cannot create
            # large bursts of target flakes.
            jitter = flake_interval * 0.20

            start_time += random.uniform(
                -jitter,
                jitter,
            )

            start_time = max(
                self.LOGO_SNOW_START,
                start_time,
            )

            # Work backward from the target based on horizontal velocity.
            # This allows the flake to drift naturally instead of homing.
            start_x = target_x - (vx * travel_time)

            # Slight imperfection makes its trajectory less suspicious.
            start_x += random.uniform(-2.0, 2.0)

            self.pending_logo_flakes.append(
                LogoFlake(
                    x=start_x,
                    y=start_y,
                    target_x=target_x,
                    target_y=target_y,
                    start_time=start_time,
                    fall_speed=speed,
                    vx=vx,
                    drift_phase=random.uniform(0, math.tau),
                    drift_amount=0.14,
                    size=self.SNOW_PARTICLE_SIZE,
                )
            )

            # Remember when the final target particle is expected to land.
            arrival_time = start_time + travel_time

            self.logo_complete_at = max(
                self.logo_complete_at,
                arrival_time,
            )

        self.pending_logo_flakes.sort(
            key=lambda flake: flake.start_time
        )

        self.pending_logo_flakes.sort(key=lambda flake: flake.start_time)

    # ==================================================
    # Lifecycle
    # ==================================================

    def start(self):
        self.active = True
        self.finished = False
        self.started_at = time.perf_counter()
        self.last_update_at = self.started_at
        self.skip_started_at = None

        self.ambient_spawn_accumulator = 0.0
        self.ambient_flakes.clear()
        self.logo_flakes.clear()
        self.settled_logo = Image.new(
            "RGBA",
            (self.game.viewport_width, self.game.viewport_height),
            (0, 0, 0, 0),
        )
        self._build_logo_flake_schedule()

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
        if not self.active or key != "z":
            return

        elapsed = time.perf_counter() - self.started_at
        if elapsed < self.SKIP_SAFETY:
            return

        if self.skip_started_at is None:
            self.skip_started_at = time.perf_counter()

    # ==================================================
    # Update
    # ==================================================

    def _spawn_ambient(self, dt):
        elapsed = time.perf_counter() - self.started_at
        if elapsed < self.SNOW_START:
            return

        self.ambient_spawn_accumulator += self.AMBIENT_FLAKES_PER_SECOND * dt

        while self.ambient_spawn_accumulator >= 1.0:
            self.ambient_spawn_accumulator -= 1.0

            self.ambient_flakes.append(
                AmbientFlake(
                    x=random.uniform(0, self.game.viewport_width - 1),
                    y=random.uniform(-12, -1),
                    vy=random.uniform(
                        self.AMBIENT_SPEED_MIN,
                        self.AMBIENT_SPEED_MAX,
                    ),
                    vx=random.uniform(
                        -self.AMBIENT_DRIFT_MAX,
                        self.AMBIENT_DRIFT_MAX,
                    ),
                    size=self.SNOW_PARTICLE_SIZE,
                    phase=random.uniform(0, math.tau),
                )
            )

    def _activate_target_flakes(self, elapsed):
        while (
            self.pending_logo_flakes
            and self.pending_logo_flakes[0].start_time <= elapsed
        ):
            self.logo_flakes.append(self.pending_logo_flakes.pop(0))

    def _update_ambient(self, dt, elapsed):
        alive = []

        for flake in self.ambient_flakes:
            flake.phase += dt * 2.0
            flake.x += flake.vx * dt + math.sin(flake.phase) * 0.14
            flake.y += flake.vy * dt

            if flake.y < self.game.viewport_height + flake.size:
                alive.append(flake)

        self.ambient_flakes = alive

    def _settle_logo_flake(self, flake):
        draw = ImageDraw.Draw(self.settled_logo)
        size = max(1, flake.size)
        x0 = int(flake.target_x)
        y0 = int(flake.target_y)

        draw.rectangle(
            (x0, y0, x0 + size - 1, y0 + size - 1),
            fill=(255, 255, 255, 255),
        )

    def _update_logo_flakes(self, dt, elapsed):
        still_falling = []

        for flake in self.logo_flakes:
            if flake.settled:
                continue

            # Move just like ordinary snow.
            flake.drift_phase += dt * 2.0

            flake.x += (
                flake.vx * dt
                + math.sin(flake.drift_phase) * flake.drift_amount
            )

            flake.y += flake.fall_speed * dt

            if flake.y >= flake.target_y:
                # Only at the instant it lands do we lock it precisely
                # onto its assigned logo pixel.
                flake.x = flake.target_x
                flake.y = flake.target_y
                flake.settled = True
                self._settle_logo_flake(flake)
            else:
                still_falling.append(flake)

        self.logo_flakes = still_falling

    def update(self):
        if not self.active:
            return

        now = time.perf_counter()

        dt = min(
            now - self.last_update_at,
            0.10
        )

        self.last_update_at = now

        elapsed = (
            now - self.started_at
        )

        # --------------------------------------------------
        # Snow keeps animating even during a Z-triggered fade.
        # --------------------------------------------------

        self._spawn_ambient(
            dt
        )

        self._activate_target_flakes(
            elapsed
        )

        self._update_ambient(
            dt,
            elapsed
        )

        self._update_logo_flakes(
            dt,
            elapsed
        )

        # --------------------------------------------------
        # Z skip
        #
        # The intro keeps updating behind the black fade.
        # Once the fade reaches full black, move on to
        # File Select.
        # --------------------------------------------------

        if self.skip_started_at is not None:

            if (
                now - self.skip_started_at
                >= self.SKIP_FADE_TIME
            ):
                self.finish()

            return

        # --------------------------------------------------
        # Normal automatic ending
        # --------------------------------------------------

        hold_end = (
            self.logo_complete_at
            + self.LOGO_HOLD_TIME
        )

        fade_end = (
            hold_end
            + self.FADE_TO_BLACK_TIME
        )

        if elapsed >= fade_end:
            self.finish()

    # ==================================================
    # Rendering
    # ==================================================

    def _black_fade_alpha(self, elapsed):
        if self.skip_started_at is not None:
            progress = (
                time.perf_counter() - self.skip_started_at
            ) / self.SKIP_FADE_TIME

            return max(
                0.0,
                min(1.0, progress),
            )

        hold_end = (
            self.logo_complete_at
            + self.LOGO_HOLD_TIME
        )

        fade_end = (
            hold_end
            + self.FADE_TO_BLACK_TIME
        )

        if elapsed <= hold_end:
            return 0.0

        if elapsed >= fade_end:
            return 1.0

        return (
            (elapsed - hold_end)
            / self.FADE_TO_BLACK_TIME
        )

    @staticmethod
    def _draw_flake(draw, x, y, size):
        x = int(round(x))
        y = int(round(y))
        size = max(1, int(size))
        draw.rectangle(
            (x, y, x + size - 1, y + size - 1),
            fill=(255, 255, 255, 255),
        )

    def _logical_frame(self):
        elapsed = time.perf_counter() - self.started_at

        frame = Image.new(
            "RGBA",
            (self.game.viewport_width, self.game.viewport_height),
            (0, 0, 0, 255),
        )

        # Settled snow IS the logo; no separate IMAGE_LOGO sprite is drawn.
        frame.alpha_composite(self.settled_logo)

        draw = ImageDraw.Draw(frame)

        for flake in self.ambient_flakes:
            self._draw_flake(draw, flake.x, flake.y, flake.size)

        for flake in self.logo_flakes:
            self._draw_flake(draw, flake.x, flake.y, flake.size)

        # The heart is the one piece visible from the very beginning.
        frame.alpha_composite(
            self.heart_pil,
            dest=(self.heart_x, self.heart_y),
        )

        fade_alpha = self._black_fade_alpha(elapsed)
        if fade_alpha > 0:
            black = Image.new(
                "RGBA",
                frame.size,
                (0, 0, 0, round(255 * fade_alpha)),
            )
            frame = Image.alpha_composite(frame, black)

        return frame

    def render(self):
        if not self.active:
            return

        self.canvas.coords(
            self.black_background,
            0,
            0,
            self.canvas.winfo_width(),
            self.canvas.winfo_height(),
        )

        logical = self._logical_frame()
        scaled_width = max(1, round(self.game.viewport_width * self.game.scale))
        scaled_height = max(1, round(self.game.viewport_height * self.game.scale))
        scaled = logical.resize(
            (scaled_width, scaled_height),
            Image.Resampling.NEAREST,
        )

        self.frame_photo = ImageTk.PhotoImage(scaled)
        self.canvas.itemconfigure(
            self.frame_item,
            image=self.frame_photo,
            state="normal",
        )
        self.canvas.coords(
            self.frame_item,
            self.game.offset_x,
            self.game.offset_y,
        )

        self.canvas.tag_raise(self.black_background)
        self.canvas.tag_raise(self.frame_item)

    def finish(self):
        if self.finished:
            return

        self.finished = True
        self.active = False

        # Keep the intro visible until game.py has installed its own black
        # overlay over File Select. Game._hide_active_startup_screen() will
        # hide our canvas items during that handoff.
        if self.on_complete is not None:
            self.on_complete()
        else:
            self.hide()
