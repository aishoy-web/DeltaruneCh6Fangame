from __future__ import annotations

import configparser
import math
import os
import shutil
import time
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageColor, ImageDraw, ImageTk

from progress import ProgressTracker
from ui_sprites import MainFont


BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# DELTARUNE FILE SELECT
# ============================================================
#
# This is a Python recreation of Chapter 5's DEVICE_MENU logic,
# adapted for a Chapter 6 fangame:
#
#   current chapter  = 6
#   previous chapter = 5
#
# The first-time Chapter 6 path is:
#
#   no filech6_0..2
#       +
#   at least one filech5_3..5
#       ->
#   MENU_PREVIOUS_FILES (GameMaker MENU_NO == 10)
#
# The class is designed to live inside Game and render over the
# same 320x240 Tkinter canvas used by ChapterIntro.
#
# Copy/erase support is included for fangame-owned Chapter 6 data.
# Starting/continuing a chapter is exposed through callbacks so
# game.py can decide how Chapter 6 should actually be initialized.
# ============================================================


UI_WIDTH = 320
UI_HEIGHT = 240

CURRENT_CHAPTER = 6
PREVIOUS_CHAPTER = 5

# GameMaker DEVICE_MENU menu numbers.
MENU_MAIN = 0
MENU_FILE_CONFIRM = 1
MENU_COPY_SOURCE = 2
MENU_COPY_TARGET = 3
MENU_COPY_OVERWRITE = 4
MENU_ERASE_SOURCE = 5
MENU_ERASE_CONFIRM = 6
MENU_ERASE_FINAL = 7
MENU_PREVIOUS_FILES = 10
MENU_PREVIOUS_CONFIRM = 11

# ------------------------------------------------------------
# Layout copied from DEVICE_MENU Create/Draw.
# ------------------------------------------------------------

XL = 210
YL = 40
YS = 5

BOX_X1 = 55
BOX_START_Y = 55

MESSAGE_X = 40
MESSAGE_Y = 30

CHAPTER_LABEL_X = 8
CHAPTER_LABEL_Y = 4

# Row text.
FILE_TEXT_X = BOX_X1 + 25
FILE_PLACE_X = BOX_X1 + 20
FILE_TIME_X = BOX_X1 + 180

# Footer.
FOOTER_LEFT_X = 54
FOOTER_MIDDLE_X = 140
FOOTER_RIGHT_X = 204
FOOTER_TOP_Y = 190
FOOTER_BOTTOM_Y = 210

# Heart targets copied from DEVICE_MENU Draw.
HEART_FILE_X = 69.5
HEART_FILE_Y = 76
HEART_FILE_STEP = YL + YS  # 45

HEART_CANCEL_X = 40
HEART_CANCEL_Y = 195

HEART_CONFIRM_A_X = 75
HEART_CONFIRM_B_X = 165
HEART_CONFIRM_Y = 81

GIANT_DOOR_ORIGIN_X = 35
GIANT_DOOR_ORIGIN_Y = 0

GIANT_DOOR_SCALE_X = 2.0
GIANT_DOOR_SCALE_Y = 2.0

# ------------------------------------------------------------
# Audio
# ------------------------------------------------------------

SFX_DIR = BASE_DIR / "sfx"

SND_MENUMOVE = SFX_DIR / "snd_menumove.wav"
SND_MENUSELECT = SFX_DIR / "snd_menuselect.wav"
SND_SWING = SFX_DIR / "snd_swing.wav"
SND_ERROR = SFX_DIR / "snd_error.wav"
SND_APPEARANCE = SFX_DIR / "AUDIO_APPEARANCE.wav"

# ------------------------------------------------------------
# Asset search roots.
#
# The GML names are kept as the preferred stems. The loader searches
# recursively under sprites/ so exported assets can live in
# sprites/intro, sprites/file_select, etc. without changing this file.
# ------------------------------------------------------------

SPRITES_DIR = BASE_DIR / "sprites"

# The Chapter 5 executable cannot know what Chapter 5's completion
# location should be when Chapter 6 displays it. Leave this empty until
# we choose the intended Chapter 5 END location. The UI will display:
#
#     [Chapter 5 END]
#
# Set e.g. CHAPTER_5_END_LOCATION = "Your Room" later if desired.
CHAPTER_5_END_LOCATION = "School Hall"

# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------

BLACK = "#000000"
WHITE = "#ffffff"
RED = "#ff0000"
YELLOW = "#ffff00"

C_LTGRAY = (192, 192, 192)
C_MAROON = (128, 0, 0)
C_NAVY = (0, 0, 128)
C_WHITE = (255, 255, 255)
C_YELLOW = (255, 255, 0)


def _merge_color(a, b, amount: float):
    """Approximate GameMaker merge_color(a, b, amount)."""
    amount = max(0.0, min(1.0, float(amount)))
    return tuple(
        round(a[i] * (1.0 - amount) + b[i] * amount)
        for i in range(3)
    )


def _hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


SUBTYPE0_COL_A = _hex(_merge_color(C_LTGRAY, C_MAROON, 0.2))
SUBTYPE0_COL_B = WHITE
SUBTYPE0_COL_PLUS = _hex(_merge_color(C_YELLOW, C_WHITE, 0.4))

SUBTYPE1_COL_A = _hex(_merge_color(C_LTGRAY, C_NAVY, 0.2))
SUBTYPE1_COL_B = WHITE
SUBTYPE1_COL_PLUS = _hex(_merge_color(C_YELLOW, C_WHITE, 0.5))


class FileSelect:
    """DELTARUNE Chapter 6 File Select.

    Parameters
    ----------
    game:
        Main Game instance. Expected to expose:
            game.root
            game.canvas
            game.scale
            game.offset_x
            game.offset_y
            game.audio

    on_continue(slot):
        Called after confirming an existing Chapter 6 FILE.

    on_new_file(slot):
        Called after confirming an empty Chapter 6 FILE.

    on_import_previous(slot, path):
        Called after confirming a Chapter 5 completion FILE.
        ``slot`` is the visible 0..2 slot.
        ``path`` points to filech5_3..5.

    on_chapter_select():
        Called when "Chapter Select" is chosen.

    on_language():
        Called when the language option is chosen.
    """

    TAG = "file_select"
    TEXT_TAG = "file_select_text"

    FRAME_MS = 16

    def __init__(
        self,
        game,
        on_continue: Optional[Callable[[int], None]] = None,
        on_new_file: Optional[Callable[[int], None]] = None,
        on_import_previous: Optional[Callable[[int, Path], None]] = None,
        on_chapter_select: Optional[Callable[[], None]] = None,
        on_language: Optional[Callable[[], None]] = None,
    ):
        self.game = game
        self.root = game.root
        self.canvas = game.canvas

        self.on_continue = on_continue
        self.on_new_file = on_new_file
        self.on_import_previous = on_import_previous
        self.on_chapter_select = on_chapter_select
        self.on_language = on_language

        self.progress = ProgressTracker()
        self.main_font = MainFont(game)

        self.visible = False
        self.active = False
        self.finished = False

        # Equivalent to DEVICE_MENU TYPE/SUBTYPE.
        self.type = 1
        self.subtype = 0

        self.incomplete_load = False

        self.menu_no = MENU_MAIN
        self.menu_coord = [0] * 12

        self.files = [False, False, False]
        self.name = ["[EMPTY]"] * 3
        self.time_ticks = [0.0] * 3
        self.time_string = ["--:--"] * 3
        self.place = ["------------"] * 3
        self.init_lang = [0] * 3

        self.complete_prev = [False, False, False]
        self.incomplete_prev = [False, False, False]

        self.complete_prev_name = ["NO DATA"] * 3
        self.complete_prev_time = [0.0] * 3
        self.complete_prev_time_string = [""] * 3
        self.complete_prev_place = [""] * 3

        self.message = " "
        self.message_timer = 0

        self.heart_x = 75.0
        self.heart_y = 110.0
        self.heart_x_cur = 75.0
        self.heart_y_cur = 75.0

        # DEVICE_MENU background state.
        self.bg_siner = 0.0
        self.bg_alpha = 0.0
        self.bg_magnitude = 6.0
        self.anim_siner = 0.0
        self.anim_siner_b = 0.0

        self._job = None
        self._last_tick = None
        self._last_layout_signature = None

        self._widgets_created = False

        self.black_background = None
        self.frame_item = None
        self.frame_photo = None

        self.heart_item = None
        self.heart_source = None
        self.heart_photo = None

        self.giant_dark_door = None
        self.image_menu = None
        self.image_menu_animation_frames = []

        self.text_photos = {}

        self.version_item = None
        self.version_photo = None

        # File Select now renders all UI into one logical 320x240 PIL
        # framebuffer.  Keeping text in the framebuffer prevents other
        # Game canvas layers from covering it on the next update tick.
        self._pil_text_cache = {}
        self._logical_text_target = None

        # Result can be inspected if callbacks are not supplied.
        # Examples:
        #   ("continue", 0)
        #   ("new", 1)
        #   ("import_previous", 2, Path(...))
        self.result = None

        self._load_assets()

    # ========================================================
    # Utility / paths
    # ========================================================

    @staticmethod
    def ini_chapter(chapter: int, slot: int) -> str:
        """Python translation of scr_ini_chapter()."""
        if chapter >= 2:
            return f"G_{chapter}_{slot}"
        return f"G{slot}"

    @staticmethod
    def time_display(ticks) -> str:
        """Python translation of scr_timedisp(); DELTARUNE uses 30 Hz ticks."""
        try:
            ticks = float(ticks)
        except (TypeError, ValueError):
            ticks = 0.0

        minutes = math.floor(ticks / 1800)
        rem_minutes = minutes % 60
        hours = (minutes - rem_minutes) // 60
        seconds = math.floor((ticks / 30) - (minutes * 60))

        return f"{int(hours)}:{int(rem_minutes):02d}:{int(seconds):02d}"

    @staticmethod
    def completed_file_name(chapter: int) -> str:
        """Python equivalent of scr_get_completed_file_name().

        Chapter 5 has no official Chapter-6-facing entry in Chapter 5's
        data.win, so its location is intentionally a project constant.
        """
        known_locations = {
            1: "Your Room",
            2: "Kris's House",
            3: "Outside Shelter",
            4: "Your Room",
            5: CHAPTER_5_END_LOCATION,
        }

        location = known_locations.get(chapter, "").strip()

        if location:
            return f"{location} [Chapter {chapter} END]"

        return f"[Chapter {chapter} END]"

    def _ui_to_screen(self, x, y):
        return (
            self.game.offset_x + x * self.game.scale,
            self.game.offset_y + y * self.game.scale,
        )

    def _official_ini_path(self):
        if self.progress.official_dir is None:
            return None
        return self.progress.official_dir / "dr.ini"

    def _fangame_ini_path(self):
        return self.progress.fangame_dir / "dr.ini"

    def _ini_candidates(self, chapter: int):
        # Mirrors ProgressTracker: official data first for Chapters 1-5,
        # fangame-owned data for Chapter 6.
        paths = []

        if chapter <= 5:
            official = self._official_ini_path()
            if official is not None:
                paths.append(official)

        paths.append(self._fangame_ini_path())
        return paths

    @staticmethod
    def _read_parser(path: Path):
        parser = configparser.ConfigParser(
            interpolation=None,
            strict=False,
        )
        parser.optionxform = str

        try:
            parser.read(path, encoding="utf-8")
        except (OSError, configparser.Error):
            return None

        return parser

    def _read_ini(self, chapter, slot, key, default=None):
        section = self.ini_chapter(chapter, slot)

        for path in self._ini_candidates(chapter):
            if not path.exists():
                continue

            parser = self._read_parser(path)
            if parser is None or not parser.has_section(section):
                continue

            # GameMaker INI keys are treated case-insensitively in practice.
            # Try exact spelling first, then a lowercase comparison.
            if parser.has_option(section, key):
                return parser.get(section, key, fallback=default)

            key_cf = key.casefold()
            for option in parser.options(section):
                if option.casefold() == key_cf:
                    return parser.get(section, option, fallback=default)

        return default
    @staticmethod
    def _clean_ini_text(value):
        text = str(value).strip()
        # Remove only matching quotation marks surrounding
        # the entire value.
        if (
            len(text) >= 2
            and text[0] == text[-1]
            and text[0] in ('"', "'")
        ):
            text = text[1:-1]

        return text
    @staticmethod
    def _clean_ini_number(value, default=0.0):
        try:
            text = str(value).strip()

            # Remove matching quotation marks around the entire value.
            if (
                len(text) >= 2
                and text[0] == text[-1]
                and text[0] in ('"', "'")
            ):
                text = text[1:-1].strip()

            return float(text)

        except (TypeError, ValueError):
            return float(default)

    def _current_file_candidates(self, slot: int):
        # ProgressTracker's final convention has no extension, while an older
        # prototype in this project used .json. Supporting both makes the new
        # File Select usable during the migration.
        stem = self.progress.fangame_dir / f"filech{CURRENT_CHAPTER}_{slot}"
        return (stem, Path(str(stem) + ".json"))

    def _current_file_exists(self, slot: int):
        if self.progress.chapter_save_file_exists_in_slot(
            CURRENT_CHAPTER,
            slot,
        ):
            return True

        return any(path.exists() for path in self._current_file_candidates(slot))

    def _previous_file_path(self, slot: int, completion: bool):
        suffix = slot + 3 if completion else slot
        filename = f"filech{PREVIOUS_CHAPTER}_{suffix}"

        for directory in self.progress._read_directories(PREVIOUS_CHAPTER):
            path = directory / filename
            if path.exists():
                return path

        return None

    # ========================================================
    # Asset loading
    # ========================================================

    @staticmethod
    def _matching_assets(stem: str):
        if not SPRITES_DIR.exists():
            return []

        stem_cf = stem.casefold()
        exact = []
        numbered = []

        for path in SPRITES_DIR.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.casefold() not in {
                ".png",
                ".gif",
                ".bmp",
                ".webp",
            }:
                continue

            p_stem = path.stem.casefold()

            if p_stem == stem_cf:
                exact.append(path)
                continue

            # Accept normal GameMaker frame exports such as:
            # IMAGE_MENU_ANIMATION_0.png
            # spr_giantdarkdoor_1.png
            prefix = stem_cf + "_"
            if p_stem.startswith(prefix):
                suffix = p_stem[len(prefix):]
                if suffix.isdigit():
                    numbered.append((int(suffix), path))

        numbered.sort(key=lambda pair: pair[0])

        return exact + [path for _, path in numbered]

    @staticmethod
    def _load_rgba(path: Path):
        return Image.open(path).convert("RGBA")

    def _load_assets(self):
        # spr_giantdarkdoor: DEVICE_MENU draws subimage 1.
        door_matches = self._matching_assets("spr_giantdarkdoor")
        if door_matches:
            chosen = door_matches[0]
            for path in door_matches:
                if path.stem.casefold().endswith("_1"):
                    chosen = path
                    break

            try:
                self.giant_dark_door = self._load_rgba(chosen)
            except OSError:
                self.giant_dark_door = None

        menu_matches = self._matching_assets("IMAGE_MENU")
        # Do not accidentally select IMAGE_MENU_ANIMATION here because
        # _matching_assets only accepts exact/numeric suffixes.
        if menu_matches:
            try:
                self.image_menu = self._load_rgba(menu_matches[0])
            except OSError:
                self.image_menu = None

        animation_matches = self._matching_assets("IMAGE_MENU_ANIMATION")
        for path in animation_matches:
            try:
                image = self._load_rgba(path)
            except OSError:
                continue

            # Some exports may produce one horizontal strip instead of one
            # PNG per GameMaker subimage.
            if image.width > UI_WIDTH and image.width % UI_WIDTH == 0:
                frame_count = image.width // UI_WIDTH
                for i in range(frame_count):
                    self.image_menu_animation_frames.append(
                        image.crop(
                            (
                                i * UI_WIDTH,
                                0,
                                (i + 1) * UI_WIDTH,
                                image.height,
                            )
                        )
                    )
            else:
                self.image_menu_animation_frames.append(image)

        heart_matches = self._matching_assets("spr_heartsmall")
        if not heart_matches:
            heart_matches = self._matching_assets("spr_heart")

        if heart_matches:
            try:
                self.heart_source = self._load_rgba(heart_matches[0])
            except OSError:
                self.heart_source = None

    # ========================================================
    # Canvas lifecycle
    # ========================================================

    def create_widgets(self):
        """Create canvas objects. Safe to call more than once."""
        if self._widgets_created:
            return

        # Keep all letterbox/widescreen space black.
        self.black_background = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill="black",
            outline="",
            state="hidden",
            tags=(self.TAG,),
        )

        # The dynamic 320x240 background + FILE boxes.
        self.frame_item = self.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=(self.TAG,),
        )

        self.version_item = self.canvas.create_image(
            0,
            0,
            anchor="se",
            state="hidden",
            tags=(self.TAG,),
        )

        self.heart_item = self.canvas.create_image(
            0,
            0,
            anchor="center",
            state="hidden",
            tags=(self.TAG,),
        )

        self._widgets_created = True

    def show(self):
        self.create_widgets()
        self.visible = True
        self.canvas.itemconfigure(
            self.black_background,
            state="normal",
        )
        self.canvas.itemconfigure(
            self.frame_item,
            state="normal",
        )
        if self.heart_item is not None:
            self.canvas.itemconfigure(
                self.heart_item,
                state="hidden",
            )
        self.canvas.tag_raise(self.black_background)
        self.canvas.tag_raise(self.frame_item)

    def hide(self):
        if not self._widgets_created:
            return

        self.visible = False
        self.canvas.itemconfigure(self.TAG, state="hidden")

    def _raise_layers(self):
        """Keep File Select's Canvas layers in a deterministic order.

        The animated framebuffer is replaced frequently.  Text, however,
        lives in separate Canvas image items.  Raising the shared TAG as one
        group can leave those layers fighting with each other on some Tk
        builds, which manifests as text appearing for one event/frame and
        then vanishing behind the framebuffer.

        Always enforce:
            black backing
            -> animated framebuffer / borders
            -> text
            -> soul cursor
        """
        if not self._widgets_created:
            return

        self.canvas.tag_raise(self.black_background)
        self.canvas.tag_raise(self.frame_item)

        # Text items may not exist yet on the very first render.
        if self.canvas.find_withtag(self.TEXT_TAG):
            self.canvas.tag_raise(self.TEXT_TAG)

        self.canvas.tag_raise(self.heart_item)

    def start(self, incomplete_load: bool = False):
        """Enter File Select and reproduce DEVICE_MENU initialization."""
        self.create_widgets()

        self.incomplete_load = bool(incomplete_load)
        self.finished = False
        self.result = None
        self.active = True

        self.bg_siner = 0.0
        self.bg_alpha = 0.0
        self.bg_magnitude = 6.0
        self.anim_siner = 0.0
        self.anim_siner_b = 0.0

        self.menu_coord = [0] * 12

        self.heart_x = 75.0
        self.heart_y = 110.0
        self.heart_x_cur = 75.0
        self.heart_y_cur = 75.0

        self.refresh_save_data()

        # DEVICE_MENU:
        # if (scr_completed_chapter_any_slot(global.chapter))
        #     SUBTYPE = 1;
        self.subtype = (
            1
            if self.progress.completed_chapter_any_slot(CURRENT_CHAPTER)
            else 0
        )

        # DEVICE_MENU INITMENU logic.
        current_any = any(self.files)
        previous_completion_any = any(self.complete_prev)

        if (
            not current_any
            and (
                previous_completion_any
                or self.incomplete_load
            )
        ):
            self.menu_no = MENU_PREVIOUS_FILES
        else:
            self.menu_no = MENU_MAIN

        self._play_menu_music()

        self._last_tick = time.perf_counter()
        self._last_layout_signature = None

        self.show()
        self.render(force_ui=True)
        self._schedule_tick()

    # Alias for menu-style code.
    open = start

    def stop(self, stop_music=True):
        self.active = False

        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

        if stop_music:
            try:
                self.game.audio.stop_music()
            except Exception:
                pass

        self.hide()

    close = stop

    # ========================================================
    # Save metadata
    # ========================================================

    def refresh_save_data(self):
        """Load current Chapter 6 and previous Chapter 5 FILE metadata."""

        for i in range(3):

            # ==================================================
            # Current Chapter 6 FILE
            # ==================================================

            self.files[i] = self._current_file_exists(i)

            if self.files[i]:
                self.name[i] = self._clean_ini_text(
                    self._read_ini(
                        CURRENT_CHAPTER,
                        i,
                        "Name",
                        "------",
                    )
                )

                raw_time = self._read_ini(
                    CURRENT_CHAPTER,
                    i,
                    "Time",
                    0,
                )

                self.time_ticks[i] = (
                    self._clean_ini_number(
                        raw_time
                    )
                )

                self.time_string[i] = (
                    self.time_display(
                        self.time_ticks[i]
                    )
                )

                self.place[i] = self._clean_ini_text(
                    self._read_ini(
                        CURRENT_CHAPTER,
                        i,
                        "Place",
                        "------------",
                    )
                )

                self.init_lang[i] = int(
                    self._clean_ini_number(
                        self._read_ini(
                            CURRENT_CHAPTER,
                            i,
                            "InitLang",
                            0,
                        )
                    )
                )

            else:
                self.name[i] = "[EMPTY]"
                self.time_ticks[i] = 0.0
                self.time_string[i] = "--:--"
                self.place[i] = "------------"
                self.init_lang[i] = 0

            # ==================================================
            # Previous Chapter 5 FILE
            # ==================================================

            self.complete_prev[i] = (
                self.progress.completed_chapter_in_slot(
                    PREVIOUS_CHAPTER,
                    i,
                )
            )

            self.incomplete_prev[i] = (
                self.progress.chapter_save_file_exists_in_slot(
                    PREVIOUS_CHAPTER,
                    i,
                )
            )

            use_file = (
                self.incomplete_prev[i]
                if self.incomplete_load
                else self.complete_prev[i]
            )

            # Incomplete files use 0..2.
            # Completion files use 3..5.
            previous_ini_slot = (
                i
                if self.incomplete_load
                else i + 3
            )

            if use_file:
                self.complete_prev_name[i] = (
                    self._clean_ini_text(
                        self._read_ini(
                            PREVIOUS_CHAPTER,
                            previous_ini_slot,
                            "Name",
                            "------",
                        )
                    )
                )

                raw_time = self._read_ini(
                    PREVIOUS_CHAPTER,
                    previous_ini_slot,
                    "Time",
                    0,
                )

                # Temporary diagnostic.
                print(
                    "[FileSelect] Chapter 5 time:",
                    self.ini_chapter(
                        PREVIOUS_CHAPTER,
                        previous_ini_slot,
                    ),
                    repr(raw_time),
                )

                self.complete_prev_time[i] = (
                    self._clean_ini_number(
                        raw_time
                    )
                )

                self.complete_prev_time_string[i] = (
                    self.time_display(
                        self.complete_prev_time[i]
                    )
                )

                if self.incomplete_load:
                    self.complete_prev_place[i] = (
                        f"Chapter {PREVIOUS_CHAPTER} FILE"
                    )
                else:
                    self.complete_prev_place[i] = (
                        self.completed_file_name(
                            PREVIOUS_CHAPTER
                        )
                    )

            else:
                self.complete_prev_name[i] = "NO DATA"
                self.complete_prev_time[i] = 0.0
                self.complete_prev_time_string[i] = ""
                self.complete_prev_place[i] = ""

    # ========================================================
    # Background
    # ========================================================

    @staticmethod
    def _set_image_alpha(image: Image.Image, alpha: float):
        alpha = max(0.0, min(1.0, alpha))

        result = image.copy()
        channel = result.getchannel("A")
        channel = channel.point(
            lambda value: round(value * alpha)
        )
        result.putalpha(channel)

        return result


    @staticmethod
    def _paste_with_origin(
        frame,
        image,
        x,
        y,
        origin_x,
        origin_y,
        xscale=1.0,
        yscale=1.0,
    ):
        dest_x = round(
            x - origin_x * xscale
        )

        dest_y = round(
            y - origin_y * yscale
        )

        frame.alpha_composite(
            image,
            dest=(dest_x, dest_y),
        )


    def _draw_subtype0_background(self, frame):
        """Reproduce the faint spr_giantdarkdoor pulse."""

        if self.giant_dark_door is None:
            return

        GIANT_DOOR_ORIGIN_X = 35
        GIANT_DOOR_ORIGIN_Y = 0

        GIANT_DOOR_SCALE_X = 2.0
        GIANT_DOOR_SCALE_Y = 2.0

        door = self.giant_dark_door.resize(
            (
                max(
                    1,
                    round(
                        self.giant_dark_door.width
                        * GIANT_DOOR_SCALE_X
                    )
                ),
                max(
                    1,
                    round(
                        self.giant_dark_door.height
                        * GIANT_DOOR_SCALE_Y
                    )
                ),
            ),
            Image.Resampling.NEAREST,
        )

        pulse_alpha = (
            0.03
            + math.sin(
                self.bg_siner / 20.0
            ) * 0.04
        )

        faint = self._set_image_alpha(
            door,
            pulse_alpha,
        )

        strong = self._set_image_alpha(
            door,
            0.25,
        )

        for x, y in (
            (43, 48),
            (47, 48),
            (43, 52),
            (47, 52),
        ):
            self._paste_with_origin(
                frame,
                faint,
                x,
                y,
                GIANT_DOOR_ORIGIN_X,
                GIANT_DOOR_ORIGIN_Y,
                GIANT_DOOR_SCALE_X,
                GIANT_DOOR_SCALE_Y,
            )

        self._paste_with_origin(
            frame,
            strong,
            45,
            50,
            GIANT_DOOR_ORIGIN_X,
            GIANT_DOOR_ORIGIN_Y,
            GIANT_DOOR_SCALE_X,
            GIANT_DOOR_SCALE_Y,
        )

    def _draw_subtype1_background(self, frame):
        """Reproduce IMAGE_MENU scanline wave + animation layers."""
        if self.image_menu is not None:
            source = self.image_menu

            if (
                source.width != UI_WIDTH
                or source.height < UI_HEIGHT
            ):
                source = source.resize(
                    (UI_WIDTH, UI_HEIGHT),
                    Image.Resampling.NEAREST,
                )

            source_alpha = self.bg_alpha * 0.8

            # GML loops 0 .. (__WAVEHEIGHT - 50) = 0..189.
            for i in range(UI_HEIGHT - 50):
                wave_minus = (
                    self.bg_magnitude
                    * (i / UI_HEIGHT)
                    * 1.3
                )

                if wave_minus > self.bg_magnitude:
                    wave_mag = 0.0
                else:
                    wave_mag = (
                        self.bg_magnitude
                        - wave_minus
                    )

                wave = (
                    math.sin(
                        (i / 8.0)
                        + (self.bg_siner / 30.0)
                    )
                    * wave_mag
                )

                row = source.crop(
                    (0, i, UI_WIDTH, i + 1)
                )

                row = self._set_image_alpha(
                    row,
                    source_alpha,
                )

                dest_y = round(
                    (-10 + i)
                    - (self.bg_alpha * 20)
                )

                frame.alpha_composite(
                    row,
                    dest=(round(wave), dest_y),
                )

                frame.alpha_composite(
                    row,
                    dest=(round(-wave), dest_y),
                )

        frames = self.image_menu_animation_frames

        if frames:
            base_index = int(
                self.anim_siner / 12.0
            )

            offsets = (0.0, 0.4, 0.8)
            alpha_multipliers = (
                0.46,
                0.56,
                0.70,
            )

            dest_y = round(
                (
                    (10 - (self.bg_alpha * 20))
                    + UI_HEIGHT
                )
                - 70
            )

            for offset, multiplier in zip(
                offsets,
                alpha_multipliers,
            ):
                index = int(
                    (self.anim_siner / 12.0)
                    + offset
                ) % len(frames)

                image = self._set_image_alpha(
                    frames[index],
                    self.bg_alpha * multiplier,
                )

                frame.alpha_composite(
                    image,
                    dest=(0, dest_y),
                )

    def _colors(self):
        if self.subtype == 1:
            return (
                SUBTYPE1_COL_A,
                SUBTYPE1_COL_B,
                SUBTYPE1_COL_PLUS,
            )

        return (
            SUBTYPE0_COL_A,
            SUBTYPE0_COL_B,
            SUBTYPE0_COL_PLUS,
        )

    def _previous_menu_for_draw(self):
        if self.menu_no == MENU_FILE_CONFIRM:
            return MENU_MAIN
        if self.menu_no == MENU_COPY_OVERWRITE:
            return MENU_COPY_TARGET
        if self.menu_no in (
            MENU_ERASE_CONFIRM,
            MENU_ERASE_FINAL,
        ):
            return MENU_ERASE_SOURCE
        if self.menu_no == MENU_PREVIOUS_CONFIRM:
            return MENU_PREVIOUS_FILES

        return self.menu_no

    def _logical_frame(self):
        frame = Image.new(
            "RGBA",
            (UI_WIDTH, UI_HEIGHT),
            (0, 0, 0, 255),
        )

        if self.subtype == 0:
            self._draw_subtype0_background(frame)
        else:
            self._draw_subtype1_background(frame)

        # Draw FILE boxes directly into the same logical framebuffer.
        draw = ImageDraw.Draw(frame, "RGBA")

        col_a, col_b, col_plus = self._colors()
        prev_menu = self._previous_menu_for_draw()

        for i in range(3):
            y1 = BOX_START_Y + ((YL + YS) * i)
            y2 = y1 + YL - 1

            draw.rectangle(
                (BOX_X1, y1, BOX_X1 + XL, y2),
                fill=(0, 0, 0, 128),
            )

            color = col_a

            if (
                0 <= prev_menu < len(self.menu_coord)
                and self.menu_coord[prev_menu] == i
            ):
                color = col_b

            if self.menu_no in (
                MENU_COPY_TARGET,
                MENU_COPY_OVERWRITE,
            ):
                if self.menu_coord[MENU_COPY_SOURCE] == i:
                    color = col_plus

            if (
                self.menu_no == MENU_ERASE_FINAL
                and self.menu_coord[MENU_ERASE_SOURCE] == i
            ):
                color = RED

            rgb = self._hex_to_rgb(color)

            draw.rectangle(
                (
                    BOX_X1 - 2,
                    y1 - 2,
                    BOX_X1 + XL + 1,
                    y2 + 1,
                ),
                outline=(*rgb, 255),
                width=2,
            )

        # Critical difference from the old implementation:
        # text and soul are part of this SAME 320x240 image.  There are no
        # independent Canvas text images for another Game render pass to cover.
        self._render_text_ui(frame)
        self._render_heart_into_frame(frame)

        return frame

    @staticmethod
    def _hex_to_rgb(color):
        color = color.lstrip("#")
        return (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16),
        )

    # ========================================================
    # Text rendering
    # ========================================================

    def _clear_text(self):
        """Remove legacy separate Canvas text items, if any exist."""
        self.canvas.delete(self.TEXT_TAG)
        self.text_photos.clear()

    def _render_text_pil(
        self,
        text,
        color=WHITE,
        scale_multiplier=1.0,
    ):
        """Render MainFont directly to a native-resolution PIL image.

        ui_sprites.MainFont normally returns a Tk PhotoImage that has already
        been scaled to the window.  That is useful for ordinary Canvas UI, but
        File Select has an animated full-screen framebuffer.  Rendering the
        glyph atlas directly here lets the text become part of that same
        framebuffer, exactly like the rest of the menu.
        """
        text = str(text)
        scale_multiplier = float(scale_multiplier or 1.0)

        if isinstance(color, str):
            rgb = ImageColor.getrgb(color)
        else:
            rgb = tuple(color[:3])

        cache_key = (
            text,
            rgb,
            round(scale_multiplier, 4),
        )

        cached = self._pil_text_cache.get(cache_key)
        if cached is not None:
            return cached

        glyph_table = getattr(MainFont, "GLYPHS", {})
        atlas = getattr(self.main_font, "mnFont", None)

        if atlas is None or not glyph_table:
            # Transparent fallback. This should only be reached if ui_sprites
            # is replaced with a MainFont implementation that has no atlas.
            image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            self._pil_text_cache[cache_key] = image
            return image

        lines = text.split("\n")
        if not lines:
            lines = [""]

        # DELTARUNE's fnt_main glyphs top out at about 16 logical pixels.
        # Calculate it from the actual table rather than hard-coding it.
        line_height = max(
            (
                int(g.get("h", 1))
                + int(g.get("offset", 0))
            )
            for g in glyph_table.values()
        )

        line_widths = []
        for line in lines:
            width = 0
            for char in line:
                glyph = glyph_table.get(char)
                if glyph is None:
                    continue
                width += int(
                    glyph.get(
                        "shift",
                        glyph.get("w", 0),
                    )
                )
            line_widths.append(width)

        width = max(1, max(line_widths, default=0))
        height = max(1, line_height * len(lines))

        image = Image.new(
            "RGBA",
            (width, height),
            (0, 0, 0, 0),
        )

        for line_index, line in enumerate(lines):
            cursor_x = 0
            base_y = line_index * line_height

            for char in line:
                glyph = glyph_table.get(char)
                if glyph is None:
                    continue

                gx = int(glyph.get("x", 0))
                gy = int(glyph.get("y", 0))
                gw = int(glyph.get("w", 0))
                gh = int(glyph.get("h", 0))
                offset = int(glyph.get("offset", 0))
                shift = int(glyph.get("shift", gw))

                if gw <= 0 or gh <= 0:
                    cursor_x += shift
                    continue

                glyph_image = atlas.crop(
                    (gx, gy, gx + gw, gy + gh)
                )

                # Preserve the font atlas alpha while replacing its RGB.
                alpha = glyph_image.getchannel("A")
                colored = Image.new(
                    "RGBA",
                    glyph_image.size,
                    (rgb[0], rgb[1], rgb[2], 255),
                )
                colored.putalpha(alpha)

                image.alpha_composite(
                    colored,
                    dest=(cursor_x, base_y + offset),
                )

                cursor_x += shift

        if scale_multiplier < 1.0:
            resampling = Image.Resampling.LANCZOS
        else:
            resampling = Image.Resampling.NEAREST

        image = image.resize(
            (
                max(
                    1,
                    round(
                        image.width
                        * scale_multiplier
                    )
                ),
                max(
                    1,
                    round(
                        image.height
                        * scale_multiplier
                    )
                ),
            ),
            resampling,
        )

        self._pil_text_cache[cache_key] = image
        return image

    @staticmethod
    def _anchor_position(x, y, image, anchor):
        """Convert a Tk-style anchor to the PIL image's top-left position."""
        x = round(x)
        y = round(y)

        if anchor in ("n", "center", "s"):
            x -= image.width // 2
        elif anchor in ("ne", "e", "se"):
            x -= image.width

        if anchor in ("w", "center", "e"):
            y -= image.height // 2
        elif anchor in ("sw", "s", "se"):
            y -= image.height

        return x, y

    def _draw_text(
        self,
        key,
        text,
        x,
        y,
        color=WHITE,
        anchor="nw",
        shadow=True,
        scale_multiplier=None,
    ):
        """Composite text directly into the current logical framebuffer."""
        target = self._logical_text_target
        if target is None:
            return

        multiplier = (
            1.0
            if scale_multiplier is None
            else float(scale_multiplier)
        )

        image = self._render_text_pil(
            text,
            color=color,
            scale_multiplier=multiplier,
        )

        px, py = self._anchor_position(
            x,
            y,
            image,
            anchor,
        )

        if shadow and str(text).strip():
            shadow_image = self._render_text_pil(
                text,
                color=BLACK,
                scale_multiplier=multiplier,
            )
            sx, sy = self._anchor_position(
                x + 1,
                y + 1,
                shadow_image,
                anchor,
            )
            target.alpha_composite(
                shadow_image,
                dest=(sx, sy),
            )

        target.alpha_composite(
            image,
            dest=(px, py),
        )

    def _row_display_data(self, i):
        if self.menu_no in (
            MENU_PREVIOUS_FILES,
            MENU_PREVIOUS_CONFIRM,
        ):
            file_found = (
                self.incomplete_prev[i]
                if self.incomplete_load
                else self.complete_prev[i]
            )

            if file_found:
                return (
                    self.complete_prev_name[i],
                    self.complete_prev_time_string[i],
                    self.complete_prev_place[i],
                )

            if self.incomplete_load:
                return (
                    "FILE not found.",
                    "",
                    "",
                )

            return (
                "Completion FILE not found.",
                "",
                "[Made on seeing credits.]",
            )

        return (
            self.name[i],
            self.time_string[i],
            self.place[i],
        )

    def _draw_rows(self):
        col_a, col_b, col_plus = self._colors()
        prev_menu = self._previous_menu_for_draw()

        for i in range(3):
            y1 = BOX_START_Y + ((YL + YS) * i)

            color = col_a

            if (
                0 <= prev_menu < len(self.menu_coord)
                and self.menu_coord[prev_menu] == i
            ):
                color = col_b

            if self.menu_no in (
                MENU_COPY_TARGET,
                MENU_COPY_OVERWRITE,
            ):
                if self.menu_coord[MENU_COPY_SOURCE] == i:
                    color = col_plus

            if (
                self.menu_no == MENU_ERASE_FINAL
                and self.menu_coord[MENU_ERASE_SOURCE] == i
            ):
                color = RED

            name, time_text, place = (
                self._row_display_data(i)
            )

            self._draw_text(
                f"row_{i}_name",
                name,
                FILE_TEXT_X,
                y1 + 5,
                color=color,
            )

            if time_text:
                self._draw_text(
                    f"row_{i}_time",
                    time_text,
                    FILE_TIME_X,
                    y1 + 5,
                    color=color,
                    anchor="ne",
                )

            confirm_this = False

            if (
                self.menu_no == MENU_FILE_CONFIRM
                and self.menu_coord[MENU_MAIN] == i
            ):
                confirm_this = True

            if (
                self.menu_no == MENU_COPY_OVERWRITE
                and self.menu_coord[MENU_COPY_TARGET] == i
            ):
                confirm_this = True

            if (
                self.menu_no
                in (
                    MENU_ERASE_CONFIRM,
                    MENU_ERASE_FINAL,
                )
                and self.menu_coord[MENU_ERASE_SOURCE] == i
            ):
                confirm_this = True

            if (
                self.menu_no == MENU_PREVIOUS_CONFIRM
                and self.menu_coord[MENU_PREVIOUS_FILES] == i
            ):
                confirm_this = True

            if confirm_this:
                self._draw_confirmation_inside_row(
                    i,
                    y1,
                    color,
                )
            else:
                if place:
                    self._draw_text(
                        f"row_{i}_place",
                        place,
                        FILE_PLACE_X,
                        y1 + 22,
                        color=color,
                    )

    def _draw_confirmation_inside_row(
        self,
        i,
        y1,
        base_color,
    ):
        col_a, col_b, _ = self._colors()

        if self.menu_no == MENU_FILE_CONFIRM:
            if self.files[i]:
                a = "Continue"
            else:
                a = "Start"
            b = "Back"
            header = " "

        elif self.menu_no == MENU_COPY_OVERWRITE:
            a = "Yes"
            b = "No"
            header = "Copy over this file?"

        elif self.menu_no == MENU_ERASE_CONFIRM:
            a = "Yes"
            b = "No"
            header = "Erase this file?"

        elif self.menu_no == MENU_ERASE_FINAL:
            a = "Yes!"
            b = "No!"
            header = "Really erase it?"

        elif self.menu_no == MENU_PREVIOUS_CONFIRM:
            a = "Start"
            b = "Back"
            header = " "

        else:
            return

        if header.strip():
            self._draw_text(
                f"confirm_header_{i}",
                header,
                FILE_TEXT_X,
                y1 + 5,
                color=base_color,
            )

        confirm_index = self.menu_coord[self.menu_no]

        color_a = (
            RED
            if self.menu_no == MENU_ERASE_FINAL
            else col_b
        ) if confirm_index == 0 else col_a

        color_b = (
            RED
            if self.menu_no == MENU_ERASE_FINAL
            else col_b
        ) if confirm_index == 1 else col_a

        self._draw_text(
            f"confirm_a_{i}",
            a,
            BOX_X1 + 35,
            y1 + 22,
            color=color_a,
        )

        self._draw_text(
            f"confirm_b_{i}",
            b,
            BOX_X1 + 125,
            y1 + 22,
            color=color_b,
        )

    def _default_message(self):
        if self.menu_no in (
            MENU_MAIN,
            MENU_FILE_CONFIRM,
        ):
            return "Please select a file."

        if self.menu_no == MENU_COPY_SOURCE:
            return "Choose a file to copy."

        if self.menu_no == MENU_COPY_TARGET:
            return "Choose a file to copy to."

        if self.menu_no == MENU_COPY_OVERWRITE:
            return "The file will be overwritten."

        if self.menu_no in (
            MENU_ERASE_SOURCE,
            MENU_ERASE_CONFIRM,
            MENU_ERASE_FINAL,
        ):
            return "Choose a file to erase."

        if self.menu_no == MENU_PREVIOUS_FILES:
            return (
                f"Start Chapter {CURRENT_CHAPTER} "
                f"from Chapter {PREVIOUS_CHAPTER}'s FILE."
            )

        if self.menu_no == MENU_PREVIOUS_CONFIRM:
            slot = (
                self.menu_coord[
                    MENU_PREVIOUS_FILES
                ]
                + 1
            )
            return (
                f"This will start Chapter {CURRENT_CHAPTER} "
                f"in FILE Slot {slot}."
            )

        return " "

    def _draw_footer(self):
        col_a, col_b, _ = self._colors()

        # ----------------------------------------------------
        # Previous Chapter FILE screen: only one cancel choice.
        # ----------------------------------------------------
        if self.menu_no in (
            MENU_PREVIOUS_FILES,
            MENU_PREVIOUS_CONFIRM,
        ):
            color = col_a

            if (
                self.menu_coord[
                    MENU_PREVIOUS_FILES
                ]
                == 3
            ):
                color = col_b

            self._draw_text(
                "prev_cancel",
                f"Don't Use Chapter {PREVIOUS_CHAPTER} FILE",
                55,
                190,
                color=color,
            )
            return

        # ----------------------------------------------------
        # Copy / erase submenus use "Cancel".
        # ----------------------------------------------------
        if self.menu_no in (
            MENU_COPY_SOURCE,
            MENU_COPY_TARGET,
            MENU_COPY_OVERWRITE,
            MENU_ERASE_SOURCE,
            MENU_ERASE_CONFIRM,
            MENU_ERASE_FINAL,
        ):
            prev = self._previous_menu_for_draw()
            color = col_b if self.menu_coord[prev] == 3 else col_a

            self._draw_text(
                "cancel",
                "Cancel",
                55,
                190,
                color=color,
            )
            return

        # ----------------------------------------------------
        # Main FILE menu.
        # ----------------------------------------------------
        if self.menu_no in (
            MENU_MAIN,
            MENU_FILE_CONFIRM,
        ):
            selected = self.menu_coord[MENU_MAIN]

            options = (
                ("Copy", 54, 190, 3),
                ("Erase", 140, 190, 4),
                (
                    f"Ch {PREVIOUS_CHAPTER} Files",
                    54,
                    210,
                    5,
                ),
                ("日本語", 136, 210, 6),
                ("Chapter Select", 204, 190, 7),
                ("End Program", 204, 210, 8),
            )

            for index, (
                text,
                x,
                y,
                menu_index,
            ) in enumerate(options):
                color = (
                    col_b
                    if selected == menu_index
                    else col_a
                )

                self._draw_text(
                    f"footer_{index}",
                    text,
                    x,
                    y,
                    color=color,
                )

    # def _draw_version(self):
    #     version = getattr(
    #         self.game,
    #         "versionno",
    #         "v23",
    #     )

    #     text = (
    #         f"DELTARUNE {version} "
    #         f"(C) Toby Fox 2018-2026"
    #     )

    #     self._draw_text(
    #         "version",
    #         text,
    #         313,
    #         236,
    #         color="#666666",
    #         anchor="se",
    #         shadow=False,
    #         scale_multiplier=0.5,
    #     )
    def _render_version_overlay(self):
        version = getattr(
            self.game,
            "versionno",
            "v0.0.0",
        )

        text = (
            f"DELTARUNE {version} "
            f"(C) Toby Fox 2018-2026, Exdwarf & Coolblubird 2026-2027"
        )

        # Render directly at final display scale.
        # MainFont multiplies this by game.scale internally.
        self.version_photo = self.main_font.render(
            text,
            color="#666666",
            scale_multiplier=0.5,
        )

        x, y = self._ui_to_screen(
            313,
            236,
        )

        self.canvas.coords(
            self.version_item,
            x,
            y,
        )

        self.canvas.itemconfigure(
            self.version_item,
            image=self.version_photo,
            state="normal",
        )

        self.canvas.tag_raise(
            self.version_item
        )

    def _render_text_ui(self, frame):
        self._logical_text_target = frame

        try:
            self._draw_rows()
            self._draw_footer()

            message = (
                self.message
                if self.message_timer > 0
                else self._default_message()
            )

            self._draw_text(
                "message",
                message,
                MESSAGE_X,
                MESSAGE_Y,
                color=self._colors()[1],
            )

            # self._draw_version()

            self._draw_text(
                "chapter_label",
                f"CHAPTER {CURRENT_CHAPTER}",
                CHAPTER_LABEL_X,
                CHAPTER_LABEL_Y,
                color=WHITE,
            )
        finally:
            self._logical_text_target = None

    # ========================================================
    # Heart
    # ========================================================

    def _heart_target(self):
        # Confirm dialogs inside a FILE row.
        if self.menu_no in (
            MENU_FILE_CONFIRM,
            MENU_COPY_OVERWRITE,
            MENU_ERASE_CONFIRM,
            MENU_ERASE_FINAL,
            MENU_PREVIOUS_CONFIRM,
        ):
            prev = self._previous_menu_for_draw()
            row = self.menu_coord[prev]
            confirm_index = self.menu_coord[self.menu_no]

            x = (
                HEART_CONFIRM_A_X
                if confirm_index == 0
                else HEART_CONFIRM_B_X
            )

            y = (
                HEART_CONFIRM_Y
                + (HEART_FILE_STEP * row)
            )

            return x, y

        selected = self.menu_coord[self.menu_no]

        if 0 <= selected <= 2:
            return (
                HEART_FILE_X,
                HEART_FILE_Y
                + (
                    HEART_FILE_STEP
                    * selected
                ),
            )

        # Footer targets from DEVICE_MENU Draw.
        targets = {
            3: (40, 195),
            4: (125, 195),
            5: (40, 215),
            6: (125, 215),
            7: (190, 195),
            8: (190, 215),
        }

        return targets.get(
            selected,
            (
                self.heart_x,
                self.heart_y,
            ),
        )

    def _update_heart(self):
        self.heart_x, self.heart_y = (
            self._heart_target()
        )

        if abs(
            self.heart_x
            - self.heart_x_cur
        ) <= 2:
            self.heart_x_cur = self.heart_x

        if abs(
            self.heart_y
            - self.heart_y_cur
        ) <= 2:
            self.heart_y_cur = self.heart_y

        self.heart_x_cur += (
            self.heart_x
            - self.heart_x_cur
        ) / 2.0

        self.heart_y_cur += (
            self.heart_y
            - self.heart_y_cur
        ) / 2.0

    def _heart_logical_image(self):
        if self.heart_source is not None:
            return self.heart_source

        logical = Image.new(
            "RGBA",
            (9, 9),
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(logical)
        draw.polygon(
            [
                (1, 2),
                (3, 0),
                (4, 2),
                (5, 0),
                (7, 2),
                (7, 4),
                (4, 8),
                (1, 4),
            ],
            fill=(255, 0, 0, 255),
        )
        return logical

    def _render_heart_into_frame(self, frame):
        logical = self._heart_logical_image()

        x = round(
            self.heart_x_cur
            - logical.width / 2
        )
        y = round(
            self.heart_y_cur
            - logical.height / 2
        )

        frame.alpha_composite(
            logical,
            dest=(x, y),
        )

    # ========================================================
    # Rendering
    # ========================================================

    def render(self, force_ui=False):
        if not self.visible:
            return

        self.canvas.coords(
            self.black_background,
            0,
            0,
            self.canvas.winfo_width(),
            self.canvas.winfo_height(),
        )

        logical = self._logical_frame()

        scaled_width = max(
            1,
            round(UI_WIDTH * self.game.scale),
        )
        scaled_height = max(
            1,
            round(UI_HEIGHT * self.game.scale),
        )

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

        # Legacy separate text/heart Canvas items are no longer used.
        if self.heart_item is not None:
            self.canvas.itemconfigure(
                self.heart_item,
                state="hidden",
            )
        self.canvas.delete(self.TEXT_TAG)

        # Match ChapterIntro's reliable layering model: one backing rectangle,
        # one complete logical framebuffer.
        self.canvas.tag_raise(self.black_background)
        self.canvas.tag_raise(self.frame_item)
        self._render_version_overlay()

    def render_static(self):
        """Compatibility with the current Game.render_static() pattern."""
        if self.visible:
            self.render()

    def render_dynamic(self):
        """Compatibility with Game.render_dynamic() if used later."""
        if self.visible:
            self.render()

    # ========================================================
    # Update loop
    # ========================================================

    def _schedule_tick(self):
        if not self.active:
            return

        if self._job is None:
            self._job = self.root.after(
                self.FRAME_MS,
                self._tick,
            )

    def _tick(self):
        self._job = None

        if not self.active:
            return

        now = time.perf_counter()

        if self._last_tick is None:
            dt = self.FRAME_MS / 1000.0
        else:
            dt = min(
                0.1,
                now - self._last_tick,
            )

        self._last_tick = now

        # Keep the same smooth timing used by the first implementation.
        # The counters are scaled by real elapsed time so the animation
        # remains stable even if Tk misses an individual callback.
        step_scale = dt * 30.0

        self.bg_siner += step_scale

        if self.subtype == 1:
            self.anim_siner += step_scale
            self.anim_siner_b += step_scale

            if self.bg_alpha < 0.5:
                self.bg_alpha += (
                    0.04
                    - (
                        self.bg_alpha
                        / 14.0
                    )
                ) * step_scale

                self.bg_alpha = min(
                    0.5,
                    self.bg_alpha,
                )

        if self.message_timer > 0:
            self.message_timer -= step_scale

            if self.message_timer <= 0:
                self.message_timer = 0
                self.message = " "
                self._last_layout_signature = None

        self._update_heart()
        self.render()

        self._schedule_tick()

    def update(self):
        """Optional external-update hook.

        FileSelect self-schedules when start() is called, so game.py does not
        need to call this. It exists for compatibility with other Game objects.
        """
        if self.active:
            self.render()

    # ========================================================
    # Audio
    # ========================================================

    def _play_sfx(self, path: Path):
        if not path.exists():
            return

        try:
            self.game.audio.play_sfx(
                str(path)
            )
        except Exception:
            pass

    def _play_menu_music(self):
        stem = (
            "quiet_church"
            if self.subtype == 1
            else "menu"
        )

        mus_dir = BASE_DIR / "mus"

        path = None

        for suffix in (
            ".ogg",
            ".mp3",
            ".wav",
        ):
            candidate = mus_dir / (
                stem + suffix
            )
            if candidate.exists():
                path = candidate
                break

        try:
            if path is not None:
                # AudioManager in this project normally accepts a music
                # filename. If a future version accepts a full path instead,
                # the fallback below covers it.
                try:
                    self.game.audio.play_music(
                        path.name
                    )
                except Exception:
                    self.game.audio.play_music(
                        str(path)
                    )
            else:
                # Let AudioManager attempt its normal lookup.
                self.game.audio.play_music(
                    stem + ".ogg"
                )
        except Exception:
            pass

    def _move_sound(self):
        self._play_sfx(SND_MENUMOVE)

    def _select_sound(self):
        self._play_sfx(SND_MENUSELECT)

    def _back_sound(self):
        self._play_sfx(SND_SWING)

    def _error_sound(self):
        self._play_sfx(SND_ERROR)

    # ========================================================
    # Input
    # ========================================================

    def handle_input(self, key):
        """Handle a key symbol from Game.key_press().

        Expected keys:
            Up, Down, Left, Right, z, x
        """
        if not self.active:
            return

        if key in ("Z",):
            key = "z"
        elif key in ("X",):
            key = "x"

        if self.menu_no == MENU_PREVIOUS_FILES:
            self._input_previous_files(key)
            return

        if self.menu_no == MENU_PREVIOUS_CONFIRM:
            self._input_two_choice(
                key,
                on_yes=self._start_previous_file,
                on_no=lambda: self._set_menu(
                    MENU_PREVIOUS_FILES
                ),
                back_menu=MENU_PREVIOUS_FILES,
            )
            return

        if self.menu_no == MENU_MAIN:
            self._input_main(key)
            return

        if self.menu_no == MENU_FILE_CONFIRM:
            self._input_two_choice(
                key,
                on_yes=self._confirm_current_file,
                on_no=lambda: self._set_menu(
                    MENU_MAIN
                ),
                back_menu=MENU_MAIN,
            )
            return

        if self.menu_no in (
            MENU_COPY_SOURCE,
            MENU_COPY_TARGET,
        ):
            self._input_copy_list(key)
            return

        if self.menu_no == MENU_COPY_OVERWRITE:
            self._input_two_choice(
                key,
                on_yes=self._finish_copy_overwrite,
                on_no=lambda: self._set_menu(
                    MENU_MAIN
                ),
                back_menu=MENU_COPY_SOURCE,
            )
            return

        if self.menu_no == MENU_ERASE_SOURCE:
            self._input_erase_list(key)
            return

        if self.menu_no == MENU_ERASE_CONFIRM:
            self._input_two_choice(
                key,
                on_yes=lambda: self._set_menu(
                    MENU_ERASE_FINAL
                ),
                on_no=lambda: self._set_menu(
                    MENU_MAIN
                ),
                back_menu=MENU_ERASE_SOURCE,
            )
            return

        if self.menu_no == MENU_ERASE_FINAL:
            self._input_two_choice(
                key,
                on_yes=self._finish_erase,
                on_no=lambda: self._set_menu(
                    MENU_MAIN
                ),
                back_menu=MENU_ERASE_SOURCE,
            )

    def _set_menu(self, menu_no):
        self.menu_no = menu_no
        self._last_layout_signature = None
        self.render(force_ui=True)

    def _input_previous_files(self, key):
        selected = self.menu_coord[
            MENU_PREVIOUS_FILES
        ]

        if key == "Down":
            if selected < 3:
                self.menu_coord[
                    MENU_PREVIOUS_FILES
                ] += 1
                self._move_sound()

        elif key == "Up":
            if selected > 0:
                self.menu_coord[
                    MENU_PREVIOUS_FILES
                ] -= 1
                self._move_sound()

        elif key == "z":
            selected = self.menu_coord[
                MENU_PREVIOUS_FILES
            ]

            if selected <= 2:
                exists = (
                    self.incomplete_prev[selected]
                    if self.incomplete_load
                    else self.complete_prev[selected]
                )

                if exists:
                    self.menu_coord[
                        MENU_PREVIOUS_CONFIRM
                    ] = 0
                    self._select_sound()
                    self._set_menu(
                        MENU_PREVIOUS_CONFIRM
                    )
                else:
                    self._error_sound()
            else:
                self._select_sound()
                self.menu_coord[MENU_MAIN] = 0
                self._set_menu(MENU_MAIN)

        elif key == "x":
            self._back_sound()
            self.menu_coord[MENU_MAIN] = 0
            self._set_menu(MENU_MAIN)

        self._last_layout_signature = None

    def _input_two_choice(
        self,
        key,
        on_yes,
        on_no,
        back_menu,
    ):
        selected = self.menu_coord[
            self.menu_no
        ]

        if key == "Left":
            if selected == 1:
                self.menu_coord[
                    self.menu_no
                ] = 0
                self._move_sound()

        elif key == "Right":
            if selected == 0:
                self.menu_coord[
                    self.menu_no
                ] = 1
                self._move_sound()

        elif key == "z":
            self._select_sound()

            if self.menu_coord[
                self.menu_no
            ] == 0:
                on_yes()
            else:
                on_no()

        elif key == "x":
            self._back_sound()
            self._set_menu(back_menu)

        self._last_layout_signature = None

    def _input_main(self, key):
        selected = self.menu_coord[
            MENU_MAIN
        ]

        if key == "Down":
            new = selected

            if selected < 3:
                new = selected + 1
            elif selected == 3:
                new = 5
            elif selected == 4:
                new = 6
            elif selected == 7:
                new = 8

            if new != selected:
                self.menu_coord[
                    MENU_MAIN
                ] = new
                self._move_sound()

        elif key == "Up":
            new = selected

            if 0 < selected < 3:
                new = selected - 1
            elif selected in (3, 4, 7):
                new = 2
            elif selected in (5, 6):
                new = selected - 2
            elif selected == 8:
                new = 7

            if new != selected:
                self.menu_coord[
                    MENU_MAIN
                ] = new
                self._move_sound()

        elif key == "Right":
            new = selected

            if 3 <= selected < 7:
                if selected == 4:
                    new = 7
                else:
                    new = selected + 1

            if new != selected:
                self.menu_coord[
                    MENU_MAIN
                ] = new
                self._move_sound()

        elif key == "Left":
            new = selected

            if selected >= 4 and selected != 5:
                if selected == 7:
                    new = 4
                elif selected == 8:
                    new = 6
                else:
                    new = selected - 1

            if new != selected:
                self.menu_coord[
                    MENU_MAIN
                ] = new
                self._move_sound()

        elif key == "z":
            selected = self.menu_coord[
                MENU_MAIN
            ]

            if selected <= 2:
                self.menu_coord[
                    MENU_FILE_CONFIRM
                ] = 0
                self._select_sound()
                self._set_menu(
                    MENU_FILE_CONFIRM
                )

            elif selected == 3:
                self.menu_coord[
                    MENU_COPY_SOURCE
                ] = 0
                self._select_sound()
                self._set_menu(
                    MENU_COPY_SOURCE
                )

            elif selected == 4:
                self.menu_coord[
                    MENU_ERASE_SOURCE
                ] = 0
                self._select_sound()
                self._set_menu(
                    MENU_ERASE_SOURCE
                )

            elif selected == 5:
                self.menu_coord[
                    MENU_PREVIOUS_FILES
                ] = 0
                self._select_sound()
                self._set_menu(
                    MENU_PREVIOUS_FILES
                )

            elif selected == 6:
                self._select_sound()
                if self.on_language is not None:
                    self.on_language()

            elif selected == 7:
                self._select_sound()
                if self.on_chapter_select is not None:
                    self.on_chapter_select()

            elif selected == 8:
                self._select_sound()
                self.stop()
                self.root.destroy()

        self._last_layout_signature = None

    # ========================================================
    # Current FILE start / continue
    # ========================================================

    def _confirm_current_file(self):
        slot = self.menu_coord[
            MENU_MAIN
        ]

        self.result = (
            "continue"
            if self.files[slot]
            else "new",
            slot,
        )

        if self.files[slot]:
            if self.on_continue is not None:
                self.stop()
                self.on_continue(slot)
            else:
                self._set_message(
                    f"Continue FILE Slot {slot + 1}.",
                    90,
                )
                self._set_menu(MENU_MAIN)
        else:
            if self.on_new_file is not None:
                self.stop()
                self.on_new_file(slot)
            else:
                self._set_message(
                    f"Start FILE Slot {slot + 1}.",
                    90,
                )
                self._set_menu(MENU_MAIN)

    # ========================================================
    # Previous Chapter FILE start
    # ========================================================

    def _start_previous_file(self):
        slot = self.menu_coord[
            MENU_PREVIOUS_FILES
        ]

        completion = not self.incomplete_load

        path = self._previous_file_path(
            slot,
            completion=completion,
        )

        if path is None:
            self._error_sound()
            self._set_menu(
                MENU_PREVIOUS_FILES
            )
            return

        self.result = (
            "import_previous",
            slot,
            path,
        )

        # This is the Python handoff corresponding to:
        #
        #   global.filechoice = FILESLOT
        #   global.filechoice += 3
        #   scr_load_prev_chapter_file(5)
        #   global.filechoice -= 3
        #   STARTGAME = 1
        #
        # We intentionally do not deserialize the full Chapter 5 save here.
        # That belongs in the Chapter 6 save/state loader, not in FileSelect.
        if self.on_import_previous is not None:
            self.stop()
            self.on_import_previous(
                slot,
                path,
            )
        else:
            self._set_message(
                (
                    f"Selected Chapter {PREVIOUS_CHAPTER} "
                    f"FILE Slot {slot + 1}."
                ),
                90,
            )
            self._set_menu(
                MENU_PREVIOUS_FILES
            )

    # ========================================================
    # Copy
    # ========================================================

    def _input_copy_list(self, key):
        menu = self.menu_no
        selected = self.menu_coord[menu]

        if key == "Down":
            if selected < 3:
                self.menu_coord[menu] += 1
                self._move_sound()

        elif key == "Up":
            if selected > 0:
                self.menu_coord[menu] -= 1
                self._move_sound()

        elif key == "x":
            self._back_sound()
            if menu == MENU_COPY_TARGET:
                self._set_menu(
                    MENU_COPY_SOURCE
                )
            else:
                self._set_menu(
                    MENU_MAIN
                )
            return

        elif key == "z":
            selected = self.menu_coord[menu]

            if selected == 3:
                self._select_sound()
                self._set_menu(MENU_MAIN)
                return

            if menu == MENU_COPY_SOURCE:
                if not self.files[selected]:
                    self._error_sound()
                    self._set_message(
                        "It can't be copied.",
                        90,
                    )
                    return

                self.menu_coord[
                    MENU_COPY_TARGET
                ] = 0
                self._select_sound()
                self._set_menu(
                    MENU_COPY_TARGET
                )
                return

            source = self.menu_coord[
                MENU_COPY_SOURCE
            ]
            target = selected

            if source == target:
                self._back_sound()
                self._set_message(
                    "You can't copy there.",
                    90,
                )
                return

            if self.files[target]:
                self.menu_coord[
                    MENU_COPY_OVERWRITE
                ] = 0
                self._select_sound()
                self._set_menu(
                    MENU_COPY_OVERWRITE
                )
            else:
                self._select_sound()
                self._copy_current_file(
                    source,
                    target,
                )
                self.refresh_save_data()
                self._set_message(
                    "Copy complete.",
                    90,
                )
                self._set_menu(
                    MENU_MAIN
                )

        self._last_layout_signature = None

    def _finish_copy_overwrite(self):
        source = self.menu_coord[
            MENU_COPY_SOURCE
        ]
        target = self.menu_coord[
            MENU_COPY_TARGET
        ]

        self._copy_current_file(
            source,
            target,
        )

        self.refresh_save_data()
        self._set_message(
            "Copy complete.",
            90,
        )
        self._set_menu(
            MENU_MAIN
        )

    def _copy_current_file(
        self,
        source,
        target,
    ):
        source_path = None

        for candidate in self._current_file_candidates(
            source
        ):
            if candidate.exists():
                source_path = candidate
                break

        if source_path is not None:
            if source_path.suffix == ".json":
                target_path = Path(
                    str(
                        self.progress.fangame_dir
                        / f"filech{CURRENT_CHAPTER}_{target}"
                    )
                    + ".json"
                )
            else:
                target_path = (
                    self.progress.fangame_dir
                    / f"filech{CURRENT_CHAPTER}_{target}"
                )

            shutil.copy2(
                source_path,
                target_path,
            )

        self._copy_ini_section(
            source,
            target,
        )

        key_source = (
            BASE_DIR
            / f"keyconfig_{source}.ini"
        )
        key_target = (
            BASE_DIR
            / f"keyconfig_{target}.ini"
        )

        if key_source.exists():
            shutil.copy2(
                key_source,
                key_target,
            )

    def _copy_ini_section(
        self,
        source,
        target,
    ):
        path = self._fangame_ini_path()

        if not path.exists():
            return

        parser = self._read_parser(path)

        if parser is None:
            return

        source_section = self.ini_chapter(
            CURRENT_CHAPTER,
            source,
        )
        target_section = self.ini_chapter(
            CURRENT_CHAPTER,
            target,
        )

        if not parser.has_section(
            source_section
        ):
            return

        if parser.has_section(
            target_section
        ):
            parser.remove_section(
                target_section
            )

        parser.add_section(
            target_section
        )

        for key, value in parser.items(
            source_section
        ):
            parser.set(
                target_section,
                key,
                value,
            )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            parser.write(file)

    # ========================================================
    # Erase
    # ========================================================

    def _input_erase_list(self, key):
        selected = self.menu_coord[
            MENU_ERASE_SOURCE
        ]

        if key == "Down":
            if selected < 3:
                self.menu_coord[
                    MENU_ERASE_SOURCE
                ] += 1
                self._move_sound()

        elif key == "Up":
            if selected > 0:
                self.menu_coord[
                    MENU_ERASE_SOURCE
                ] -= 1
                self._move_sound()

        elif key == "x":
            self._back_sound()
            self._set_menu(MENU_MAIN)
            return

        elif key == "z":
            selected = self.menu_coord[
                MENU_ERASE_SOURCE
            ]

            if selected == 3:
                self._select_sound()
                self._set_menu(MENU_MAIN)
                return

            if not self.files[selected]:
                self._error_sound()
                self._set_message(
                    "There's nothing to erase.",
                    90,
                )
                return

            self.menu_coord[
                MENU_ERASE_CONFIRM
            ] = 0
            self._select_sound()
            self._set_menu(
                MENU_ERASE_CONFIRM
            )

        self._last_layout_signature = None

    def _finish_erase(self):
        slot = self.menu_coord[
            MENU_ERASE_SOURCE
        ]

        self._erase_current_file(slot)
        self.refresh_save_data()

        self._play_sfx(
            SND_APPEARANCE
        )

        self._set_message(
            "Erase complete.",
            90,
        )

        self._set_menu(MENU_MAIN)

    def _erase_current_file(self, slot):
        for path in self._current_file_candidates(
            slot
        ):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

        keyconfig = (
            BASE_DIR
            / f"keyconfig_{slot}.ini"
        )

        try:
            keyconfig.unlink()
        except FileNotFoundError:
            pass

        ini_path = self._fangame_ini_path()

        parser = self._read_parser(
            ini_path
        ) if ini_path.exists() else configparser.ConfigParser(
            interpolation=None
        )

        parser.optionxform = str

        section = self.ini_chapter(
            CURRENT_CHAPTER,
            slot,
        )

        if not parser.has_section(section):
            parser.add_section(section)

        defaults = {
            "Name": "[EMPTY]",
            "Level": "0",
            "Love": "0",
            "Time": "0",
            "Room": "0",
            "Date": "0",
            "UraBoss": "0",
            "SideB": "0",
            "Version": "0",
        }

        for key, value in defaults.items():
            parser.set(
                section,
                key,
                value,
            )

        with ini_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            parser.write(file)

    # ========================================================
    # Temporary message helper
    # ========================================================

    def _set_message(
        self,
        text,
        frames=90,
    ):
        self.message = str(text)
        self.message_timer = float(frames)
        self._last_layout_signature = None
        self.render(force_ui=True)


# Backward-compatible alias for the older game.py prototype that imports
# `FileMenu`. This lets you switch:
#
#     from filemenu import FileMenu
#
# to:
#
#     from fileselect import FileMenu
#
# without changing the rest of that initialization immediately.
FileMenu = FileSelect
