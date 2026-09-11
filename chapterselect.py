from importlib.resources import path
import os
import tkinter as tk
import time
import pygame
import subprocess
import sys
import tempfile
from PIL import Image, ImageTk, ImageDraw, ImageGrab
from pathlib import Path
from ui_sprites import MainFont
from audiomanager import AudioManager
from progress import ProgressTracker


BASE_DIR = Path(__file__).resolve().parent
"""
Chapter Select screen
Chapter Select architecture.

Logical Chapter Select resolution:
    320 x 240

This is centered vertically inside the game's
320 x 240 logical viewport.
"""

# ------------------------------------------------------
# Chapter Select UI layout
# ------------------------------------------------------

UI_WIDTH = 320
UI_HEIGHT = 240

# Chapter rows
CHAPTER_START_Y = 8
CHAPTER_SPACING = 30

CHAPTER_TEXT_X = 25
CHAPTER_TITLE_X = 180

CHAPTER_ICON_X = 289.5
CHAPTER_ICON_Y_OFFSET = 8.5
CHAPTER_TITLE_Y_OFFSET = 8

# Completion stars
STAR_X = 108

# Horizontal dividers
BAR_X = 0
BAR_WIDTH = 320
BAR_Y_OFFSET = 22.75
BAR_HEIGHT = 1.25

# Soul cursor
CURSOR_X = 14.5
CURSOR_Y_OFFSET = 8.5

# Footer
FOOTER_QUIT_X = 119
FOOTER_LANGUAGE_X = 165
FOOTER_Y = 224.5

# Copyright / version information
FOOTER_INFO_X = 8
FOOTER_INFO_Y = 218

# Independent scale for copyright information.
# This is multiplied by the normal viewport scale.
FOOTER_INFO_SCALE = .5

# Distance from the bottom of the logical viewport.
FOOTER_INFO_BOTTOM_MARGIN = 4

# Footer cursor
FOOTER_CURSOR_QUIT_X = 94.5
FOOTER_CURSOR_LANGUAGE_X = 165

# Chapter confirmation
CONFIRM_HEART_X = 120
CONFIRM_PLAY_X = 140
CONFIRM_DONOT_X = 220
CONFIRM_Y_OFFSET = 8.5

CHAPTER_STAR_X = 92.5
CHAPTER_STAR_Y_OFFSET = 2
CHAPTER_STAR_SPACING = 6

SHADOW_GRID_X = 294.5
SHADOW_GRID_Y = 220.5
SHADOW_GRID_SPACING = 10
SHADOW_GRID_SLOT_SPACING = 5
SHADOW_GRID_COLUMN_SPACING = 10

# ------------------------------------------------------
# Colors
# ------------------------------------------------------

BLACK = "#000000"
WHITE = "#fefefe"
GRAY = "#7f7f7f"
DARK_GRAY = "#2b2b2b"
YELLOW = "#fefe00"

# ------------------------------------------------------
# Assets
# ------------------------------------------------------

CHAPTER_ICON_SHEET = (
    BASE_DIR
    / "sprites"
    / "chapter_select"
    / "spr_chapterIcon.png"
)

HEART_PATH = (
    BASE_DIR
    / "sprites"
    / "chapter_select"
    / "spr_heart.png"
)

STAR_PATH = (
    BASE_DIR
    / "sprites"
    / "chapter_select"
    / "spr_ui_star"
)

AUDIO_DRONE = (
    BASE_DIR
    /"mus"
    /"AUDIO_DRONE"
)

DOT_PATH = (
    BASE_DIR
    / "sprites"
    / "chapter_select"
    / "spr_ui_dot"
)

SFX_DIR = BASE_DIR / "sfx"

SND_SWING = SFX_DIR / "snd_swing.wav"
SND_MENUMOVE = SFX_DIR / "snd_menumove.wav"
SND_MENUSELECT = SFX_DIR / "snd_menuselect.wav"

CH6_SELECT = (
    BASE_DIR
    / "wip_music"
    / "ch6_select_even_less_old.wav"
)

CHAPTER6_ENTRY = BASE_DIR / "chapter6.py"

# ------------------------------------------------------
# Chapter launch transition
#
# Original obj_screen_transition Step:
#     fadeout = lerp(fadeout, 0, 0.125)
#     xscale *= 0.95
#     yscale *= 0.99
#     yy *= 0.99
#
# The Chapter Select is captured as one image, then that
# image is transformed over a black background.
# ------------------------------------------------------

TRANSITION_FRAME_MS = 33
TRANSITION_BGM_FADE_MS = 500

TRANSITION_ALPHA_LERP = 0.125
TRANSITION_X_SCALE_MULTIPLIER = 0.95
TRANSITION_Y_SCALE_MULTIPLIER = 0.99
TRANSITION_Y_MULTIPLIER = 0.99

# ------------------------------------------------------
# Entrance animation
#
# Original GameMaker values:
#     y -= 40
#     alpha = lerp(alpha, 1, 0.06)
#     y = lerp(y, ystart, 0.14)
#
# The original UI is 640x480, so the 40px movement
# becomes 20px in our 320x240 logical viewport.
# ------------------------------------------------------

ENTRANCE_START_Y_OFFSET = -20.0

ENTRANCE_ALPHA_LERP = 0.1
ENTRANCE_Y_LERP = 0.22

# Approximately one GameMaker Step at 60 FPS.
ENTRANCE_FRAME_MS = 4

# Python's lerp approaches 1 without naturally landing
# there, so snap to the final state once extremely close.
ENTRANCE_ALPHA_THRESHOLD = 0.999

# ------------------------------------------------------
# Startup completion prompt
#
# Translation of obj_screen_start / obj_ui_choice.
# Original launcher coordinates are 640x480, so all
# positions below are their half-resolution equivalents.
# ------------------------------------------------------

STARTUP_PROMPT_X = UI_WIDTH / 2
STARTUP_PROMPT_Y = 110

STARTUP_CHOICE_X = UI_WIDTH / 2
STARTUP_CHOICE_START_Y = 130
STARTUP_CHOICE_SPACING = 20

STARTUP_HEART_GAP = 15
STARTUP_HEART_Y_OFFSET = 8

STARTUP_VERSION_X = 8
STARTUP_VERSION_Y = 225
STARTUP_VERSION_SCALE = 0.5

STARTUP_START_Y_OFFSET = -20.0
STARTUP_ALPHA_LERP = 0.06
STARTUP_Y_LERP = 0.14
STARTUP_INPUT_DELAY_STEPS = 6
STARTUP_FRAME_MS = 33
STARTUP_ALPHA_THRESHOLD = 0.999

class ChapterSelect:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DELTARUNE")
        self.root.attributes("-fullscreen", True)
        icon_path = BASE_DIR / "sprites" / "assets" / "taskbar_logo.png"
        icon = ImageTk.PhotoImage(Image.open(icon_path))
        self.root.iconphoto(False, icon)
        self.icon = icon
        self.canvas = tk.Canvas(
            self.root,
            width=320,
            height=240,
            bg="black",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.shadow_grid_photos = []
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.main_font = MainFont(self)
        self.audio = AudioManager()
        self.progress = ProgressTracker()
        self.main_font_images = {}
        self.footer_info_photo = None
        self.selection = "chapters"
        self.chapter_index = 0
        self.footer_index = 0
        self.confirm_index = 0
        self.handoff_pending = False
        self.star_photos = []
        self.chapters = []
        self.available_chapters = 6

        self.transitioning = False
        self.fade_alpha = 0

        # ==================================================
        # Chapter launch transition
        # ==================================================

        self.chapter_process = None
        self.chapter_ready_file = None
        self.handoff_job = None

        self.transition_job = None
        self.transition_start_time = None
        self.transition_duration_ms = 0

        self.transition_fadeout = 1.0
        self.transition_xscale = 1.0
        self.transition_yscale = 1.0
        self.transition_yy = UI_HEIGHT / 2

        self.transition_source_image = None
        self.transition_photo = None
        self.transition_image_item = None
        self.transition_black_item = None

        self.chapter_confirm_sound = None
        self.chapter_confirm_channel = None

        # ==================================================
        # Chapter Select entrance animation
        # ==================================================

        self.entrance_active = True
        self.entrance_alpha = 0.0
        self.entrance_y_offset = ENTRANCE_START_Y_OFFSET
        self.entrance_job = None

        # ==================================================
        # Startup completion prompt
        # ==================================================

        self.startup_prompt_active = False
        self.startup_prompt_type = None
        self.startup_completed_chapter = 0
        self.startup_in_progress_chapter = 0
        self.startup_choice_index = 0
        self.startup_alpha = 0.0
        self.startup_y_offset = STARTUP_START_Y_OFFSET
        self.startup_timer = 0
        self.startup_input_enabled = False
        self.startup_job = None

        self.startup_prompt_photo = None
        self.startup_choice_photos = []
        self.startup_heart_photo = None
        self.startup_version_photo = None
        self.startup_items = []

        self.keys_pressed = set()
        self.selected_chapter = None

        self.canvas_items = []
        self.icon_images = []

        self.root.bind("<Configure>", self.update_scale)
        self.root.bind("<KeyPress>", self.key_press)
        self.root.bind("<KeyRelease>", self.key_release)

        # ==================================================
        # Assets / data
        # ==================================================

        self.load_assets()
        self.create_chapters()
        self.refresh_progress()
        self.determine_startup_prompt()

        # ==================================================
        # Canvas
        # ==================================================

        self.create_widgets()

    def play_sfx(self, path):
        self.audio.play_sfx(str(path))

    # ======================================================
    # ASSETS
    # ======================================================

    def update_scale(self, event=None):

        screen_width = self.canvas.winfo_width()
        screen_height = self.canvas.winfo_height()

        if screen_width <= 1 or screen_height <= 1:
            return

        # Maintain the game's 320x240 aspect ratio.
        self.scale = min(
            screen_width / UI_WIDTH,
            screen_height / UI_HEIGHT
        )

        # Size of the scaled 320x240 viewport.
        scaled_width = UI_WIDTH * self.scale
        scaled_height = UI_HEIGHT * self.scale

        # Center the viewport in the fullscreen window.
        self.offset_x = (
            screen_width - scaled_width
        ) / 2

        self.offset_y = (
            screen_height - scaled_height
        ) / 2

        self.render()

    def key_press(self, event):
        key = event.keysym
        if self.transitioning:
            return
        if key in self.keys_pressed:
            return
        self.keys_pressed.add(key)
        self.handle_input(key)
    def key_release(self, event):
        self.keys_pressed.discard(event.keysym)

    def run(self):

        if self.startup_prompt_active:

            # obj_CHAPTER_SELECT stops the drone while
            # obj_screen_start is visible.
            self.audio.stop_music()

            self.render()

            self.startup_job = self.root.after(
                STARTUP_FRAME_MS,
                self.update_startup_prompt
            )

        else:

            self.start_normal_chapter_select()

        self.root.mainloop()

        return self.selected_chapter

    def load_assets(self):

        self.chapter_icon_sheet = Image.open(
            CHAPTER_ICON_SHEET
        ).convert("RGBA")
        self.dot_frames = []

        for i in range(2):

            dot_path = (
                DOT_PATH
                / f"spr_ui_dot_{i}.png"
            )

            self.dot_frames.append(
                Image.open(
                    dot_path
                ).convert("RGBA")
            )
        self.chapter_icons = self.extract_chapter_icons()
        self.heart_image = Image.open(
            HEART_PATH
        ).convert("RGBA")
        self.star_frames = []

        for i in range(3):

            star_path = (
                STAR_PATH
                / f"spr_ui_star_{i}.png"
            )

            if star_path.exists():

                frame = Image.open(
                    star_path
                ).convert("RGBA")

                self.star_frames.append(
                    frame
                )

    def refresh_progress(self):
        for chapter in self.chapters:
            number = chapter["number"]
            # ----------------------------------------------
            # Chapter completion
            # ----------------------------------------------
            completion_slots = (
                self.progress.completion_slots(
                    number
                )
            )
            chapter[
                "completion_slots"
            ] = completion_slots
            chapter[
                "completed"
            ] = any(
                state > 0
                for state in completion_slots
            )
            # ----------------------------------------------
            # Secret boss / URA
            # ----------------------------------------------
            chapter[
                "ura_results"
            ] = [
                self.progress.get_ura_value(
                    number,
                    slot
                )
                for slot in range(3)
            ]

        # ----------------------------------------------
        # Shadow Crystal grid
        # ----------------------------------------------

        self.shadow_crystal_grid = (
            self.progress.shadow_crystal_grid(
                maximum_chapter=6
            )
        )

    def determine_startup_prompt(self):
        """
        Reproduce the relevant obj_CHAPTER_SELECT startup-state
        precedence for this Chapter 6 launcher.

        The original launcher first finds the highest unfinished
        chapter that has a normal save, then the highest completed
        chapter. Its resulting precedence is:

            * unfinished next chapter -> Continue prompt
            * otherwise completed chapter -> Play next prompt
            * a gap of 2+ chapters -> normal Chapter Select
            * latest available chapter completed -> normal Chapter Select

        This Python project currently launches Chapter 6, so startup
        prompts are only activated when their target chapter is 6.
        """

        highest_completed = 0
        highest_in_progress = 0

        for chapter in range(
            1,
            self.available_chapters + 1
        ):

            completed = (
                self.progress.completed_chapter_any_slot(
                    chapter
                )
            )

            if completed:
                highest_completed = chapter

            if (
                self.progress.chapter_save_file_exists(
                    chapter
                )
                and not completed
            ):
                highest_in_progress = chapter

        self.startup_completed_chapter = (
            highest_completed
        )
        self.startup_in_progress_chapter = (
            highest_in_progress
        )

        prompt_type = None
        target_chapter = 0

        # Equivalent to the Value_2 / Value_3 / Value_4
        # precedence in obj_CHAPTER_SELECT.init().
        if highest_completed >= self.available_chapters:
            prompt_type = None

        elif highest_completed > 0:

            if highest_in_progress > highest_completed:

                if (
                    highest_in_progress
                    - highest_completed
                ) >= 2:
                    prompt_type = None

                else:
                    prompt_type = "continue"
                    target_chapter = (
                        highest_in_progress
                    )

            else:
                prompt_type = "completed"
                target_chapter = (
                    highest_completed + 1
                )

        elif highest_in_progress > 0:
            prompt_type = "continue"
            target_chapter = highest_in_progress

        # This fangame currently has an executable launch path only
        # for Chapter 6. Do not strand the player on a startup prompt
        # whose Yes/Play option cannot be launched by this program.
        if target_chapter != 6:
            prompt_type = None

        self.startup_prompt_type = prompt_type
        self.startup_prompt_active = (
            prompt_type is not None
        )

        if self.startup_prompt_active:

            self.selection = "startup"
            self.startup_choice_index = 0
            self.startup_alpha = 0.0
            self.startup_y_offset = (
                STARTUP_START_Y_OFFSET
            )
            self.startup_timer = 0
            self.startup_input_enabled = False

            # obj_CHAPTER_SELECT calls stop_bgm() for both the
            # Continue and completed-chapter startup screens.
            self.entrance_active = False

    def render_shadow_crystals(self):

        # IMPORTANT:
        # Keep the old PhotoImage references alive until
        # every canvas item has either been hidden or assigned
        # a new image.
        old_photos = self.shadow_grid_photos

        new_photos = []

        # --------------------------------------------------
        # Hide existing grid items first while their old
        # PhotoImages still exist.
        # --------------------------------------------------

        for column in self.shadow_grid_items:

            for item in column:

                self.canvas.itemconfigure(
                    item,
                    state="hidden"
                )

        grid = self.shadow_crystal_grid

        chapter_count = len(grid)

        if chapter_count == 0:

            self.shadow_grid_photos = []
            return

        # --------------------------------------------------
        # Original GameMaker:
        #
        # max_width = 20 * highest_chapter_obtained;
        # x_offset = max_width / 2;
        #
        # Half-resolution equivalent:
        # --------------------------------------------------

        max_width = (
            SHADOW_GRID_COLUMN_SPACING
            * chapter_count
        )

        x_offset = (
            max_width / 2
        )

        for column_index, chapter_data in enumerate(
            grid
        ):

            results = chapter_data[
                "results"
            ]

            x = (
                SHADOW_GRID_X
                + (
                    column_index
                    * SHADOW_GRID_COLUMN_SPACING
                )
                - x_offset
            )

            for slot_index, result in enumerate(
                results
            ):

                frame_index = (
                    1
                    if result > 0
                    else 0
                )

                dot = self.dot_frames[
                    frame_index
                ].copy()

                # Participate in the entrance animation.
                dot = self.apply_entrance_alpha(
                    dot
                )

                dot_scale = (
                    self.scale
                    * 0.5
                )

                dot = dot.resize(
                    (
                        max(
                            1,
                            round(
                                dot.width
                                * dot_scale
                            )
                        ),
                        max(
                            1,
                            round(
                                dot.height
                                * dot_scale
                            )
                        )
                    ),
                    Image.Resampling.NEAREST
                )

                photo = ImageTk.PhotoImage(
                    dot
                )

                # Keep the new image alive.
                new_photos.append(
                    photo
                )

                y = (
                    SHADOW_GRID_Y
                    + self.entrance_y_offset
                    + (
                        slot_index
                        * SHADOW_GRID_SLOT_SPACING
                    )
                )

                screen_x, screen_y = (
                    self.ui_to_screen(
                        x,
                        y
                    )
                )

                item = (
                    self.shadow_grid_items[
                        column_index
                    ][
                        slot_index
                    ]
                )

                self.canvas.coords(
                    item,
                    screen_x,
                    screen_y
                )

                self.canvas.itemconfigure(
                    item,
                    image=photo,
                    state="normal"
                )

        # Only NOW may the old PhotoImages be released.
        self.shadow_grid_photos = new_photos
    def extract_dot_frames(self):
        """
        spr_ui_dot has two subimages:

            frame 0 = unlit
            frame 1 = obtained
        """

        frame_width = (
            self.dot_sheet.width // 2
        )

        frame_height = (
            self.dot_sheet.height
        )

        frames = []

        for i in range(2):

            left = (
                i * frame_width
            )

            frame = self.dot_sheet.crop(
                (
                    left,
                    0,
                    left + frame_width,
                    frame_height
                )
            )

            frames.append(frame)

        return frames
    def shadow_grid_x(
        self,
        index,
        count
    ):

        max_width = (
            SHADOW_GRID_SPACING
            * count
        )

        x_offset = (
            max_width / 2
        )

        return (
            SHADOW_GRID_X
            + (
                index
                * SHADOW_GRID_SPACING
            )
            - x_offset
        )


    # ======================================================
    # CHAPTER ICONS
    # ======================================================

    def extract_chapter_icons(self):

        """
        Extract the six actual Chapter Select icons.

        spr_chapterIcon contains one unused/blank frame first,
        followed by the six chapter icons.

        Each frame is 26x27 pixels with 1 pixel between frames.
        """

        sheet = self.chapter_icon_sheet

        icon_width = 26
        icon_height = 23

        start_x = 28
        start_y = 15
        spacing = 27

        icons = []

        for index in range(6):

            left = start_x + index * spacing
            top = start_y

            right = left + icon_width
            bottom = top + icon_height

            icons.append(
                sheet.crop(
                    (
                        left,
                        top,
                        right,
                        bottom
                    )
                )
            )

        return icons

    # ======================================================
    # CHAPTER DATA
    # ======================================================

    def create_chapters(self):

        self.chapters = [
            {
                "number": 1,
                "title": "The Beginning",
                "icon": 1,
                "unlocked": True,
            },

            {
                "number": 2,
                "title": "A Cyber's World",
                "icon": 2,
                "unlocked": True,
            },

            {
                "number": 3,
                "title": "Late Night",
                "icon": 3,
                "unlocked": True,
            },

            {
                "number": 4,
                "title": "Prophecy",
                "icon": 4,
                "unlocked": True,
            },

            {
                "number": 5,
                "title": "Festival Day",
                "icon": 5,
                "unlocked": True,
            },

            {
                "number": 6,
                "title": "Angel's Haven",
                "icon": 6,
                "unlocked": True,
            },

            {
                "number":7,
                "title": "- -",
                "icon": 0,
                "unlocked": False
            }
        ]

    def create_background(self):
        x1, y1 = self.ui_to_screen(0, 0)
        x2, y2 = self.ui_to_screen(320, 240)

        self.background = self.canvas.create_rectangle(
            x1, y1,
            x2, y2,
            fill="black",
            outline="",
            tags="chapter_select"
        )

    # ======================================================
    # CANVAS
    # ======================================================

    def create_widgets(self):

        self.background = self.canvas.create_rectangle(
            0,
            0,
            320,
            240,
            fill=BLACK,
            outline="",
            tags=("chapter_select",)
        )

        self.canvas_items.append(self.background)

        # --------------------------------------------------
        # Chapter rows
        # --------------------------------------------------

        self.chapter_text_items = []
        self.chapter_title_items = []
        self.chapter_icon_items = []
        self.chapter_star_items = []
        self.chapter_bar_items = []

        for i in range(7):

            chapter_text = self.canvas.create_image(
            0,
            0,
            anchor="nw",
            tags=("chapter_select",)
        )

            title_text = self.canvas.create_image(
            0,
            0,
            anchor="center",
            tags=("chapter_select",)
        )

            icon_item = self.canvas.create_image(
                0,
                0,
                anchor="center",
                tags=("chapter_select",)
            )

            bar_item = self.canvas.create_rectangle(
                0,
                0,
                0,
                0,
                fill=DARK_GRAY,
                outline="",
                tags=("chapter_select",)
            )

            self.chapter_text_items.append(
                chapter_text
            )

            self.chapter_title_items.append(
                title_text
            )

            self.chapter_icon_items.append(
                icon_item
            )

            self.chapter_bar_items.append(
                bar_item
            )

            self.canvas_items.extend(
                [
                    chapter_text,
                    title_text,
                    icon_item,
                    bar_item,
                ]
            )

        # --------------------------------------------------
        # Stars
        # --------------------------------------------------

        self.star_items = []

        for chapter in self.chapters:

            stars = []

            # Three save slots = three star states.
            for _ in range(3):

                item = self.canvas.create_image(
                    0,
                    0,
                    anchor="center",
                    state="hidden",
                    tags=("chapter_select",)
                )

                stars.append(item)
                self.canvas_items.append(item)

            self.star_items.append(stars)

        # --------------------------------------------------
        # Soul cursor
        # --------------------------------------------------

        self.cursor = self.canvas.create_image(
            0,
            0,
            anchor="center",
            tags=("chapter_select",)
        )

        self.canvas_items.append(self.cursor)

        # --------------------------------------------------
        # Footer
        # --------------------------------------------------

        self.quit_item = self.canvas.create_image(
            0,
            0,
            anchor="center",
            tags=("chapter_select",)
        )

        self.language_item = self.canvas.create_image(
            0,
            0,
            anchor="center",
            tags=("chapter_select",)
        )

        self.footer_info = self.canvas.create_image(
            0,
            0,
            anchor="nw",
            tags=("chapter_select",)
        )

        self.canvas_items.extend(
            [
                self.quit_item,
                self.language_item,
                self.footer_info,
            ]
        )

        self.update_assets()

        # --------------------------------------------------
        # Chapter confirmation
        # --------------------------------------------------

        self.play_item = self.canvas.create_image(
            0,
            0,
            anchor="center",
            tags=("chapter_select",)
        )

        self.do_not_item = self.canvas.create_image(
            0,
            0,
            anchor="center",
            tags=("chapter_select",)
        )

        self.confirm_cursor = self.canvas.create_image(
            0,
            0,
            anchor="center",
            tags=("chapter_select",)
        )

        self.canvas_items.extend(
            [
                self.play_item,
                self.do_not_item,
                self.confirm_cursor,
            ]
        )
        # --------------------------------------------------
        # Shadow Crystal grid
        # --------------------------------------------------

        self.shadow_grid_items = []

        for chapter_index in range(6):

            column = []

            for slot_index in range(3):

                item = self.canvas.create_image(
                    0,
                    0,
                    anchor="center",
                    state="hidden",
                    tags=("chapter_select",)
                )

                column.append(item)

                self.canvas_items.append(
                    item
                )

            self.shadow_grid_items.append(
                column
            )

        # --------------------------------------------------
        # Startup completion prompt
        # --------------------------------------------------

        self.startup_prompt_text_item = (
            self.canvas.create_image(
                0,
                0,
                anchor="n",
                state="hidden",
                tags=("startup_prompt",)
            )
        )

        self.startup_choice_items = []

        for _ in range(2):

            item = self.canvas.create_image(
                0,
                0,
                anchor="n",
                state="hidden",
                tags=("startup_prompt",)
            )

            self.startup_choice_items.append(
                item
            )

        self.startup_cursor_item = (
            self.canvas.create_image(
                0,
                0,
                anchor="center",
                state="hidden",
                tags=("startup_prompt",)
            )
        )

        self.startup_version_item = (
            self.canvas.create_image(
                0,
                0,
                anchor="nw",
                state="hidden",
                tags=("startup_prompt",)
            )
        )

        self.startup_items = [
            self.startup_prompt_text_item,
            *self.startup_choice_items,
            self.startup_cursor_item,
            self.startup_version_item,
        ]

    def color_with_alpha(self, color, alpha):
        """
        Simulate draw alpha against this screen's black background.
        """

        color = color.lstrip("#")

        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)

        alpha = max(
            0.0,
            min(1.0, alpha)
        )

        r = round(r * alpha)
        g = round(g * alpha)
        b = round(b * alpha)

        return f"#{r:02x}{g:02x}{b:02x}"

    def fade_color(self, color):
        """
        Apply the normal Chapter Select entrance alpha.
        """

        return self.color_with_alpha(
            color,
            self.entrance_alpha
        )

    def apply_entrance_alpha(self, image):
        """
        Apply the entrance alpha to a PIL RGBA image.

        Used for chapter icons and the soul cursor.
        """

        image = image.copy()

        alpha = max(
            0.0,
            min(1.0, self.entrance_alpha)
        )

        if alpha >= 1.0:
            return image

        alpha_channel = image.getchannel("A")

        alpha_channel = alpha_channel.point(
            lambda value: round(value * alpha)
        )

        image.putalpha(alpha_channel)

        return image

    # ======================================================
    # COORDINATES
    # ======================================================

    def ui_to_screen(self, x, y):

        return (
            self.offset_x + x * self.scale,
            self.offset_y + y * self.scale
        )

    # ======================================================
    # OPEN / CLOSE
    # ======================================================

    def open(self):

        self.selection = "chapters"

        # Original Chapter Select highlights the highest
        # revealed chapter.
        self.chapter_index = (
            self.available_chapters - 1
        )

        self.footer_index = 0
        self.confirm_index = 0

        self.show()
        self.render()

    def close(self):
        self.audio.stop_music()
        self.hide()

    # ======================================================
    # VISIBILITY
    # ======================================================

    def show(self):

        for item in self.startup_items:

            self.canvas.itemconfigure(
                item,
                state="hidden"
            )

        for item in self.canvas_items:

            self.canvas.itemconfigure(
                item,
                state="normal"
            )

    def hide(self):

        for item in self.canvas_items:

            self.canvas.itemconfigure(
                item,
                state="hidden"
            )

        for item in self.startup_items:

            self.canvas.itemconfigure(
                item,
                state="hidden"
            )

    # ======================================================
    # RENDER
    # ======================================================

    def render(self):

        # During the launch transition, the live Chapter
        # Select is replaced by a captured image, just like
        # obj_screen_transition drawing spr_aftereffect.
        if self.transitioning:
            return

        if self.startup_prompt_active:

            self.render_startup_prompt()
            return

        # Make sure the startup prompt cannot remain visible
        # after switching to the normal Chapter Select.
        for item in self.startup_items:

            self.canvas.itemconfigure(
                item,
                state="hidden"
            )

        self.update_assets()

        self.render_chapters()
        self.render_stars()
        self.render_footer()
        self.render_shadow_crystals()

        if self.selection == "confirm":

            self.render_confirmation()

        else:

            self.render_cursor()

            # Make sure confirmation elements are hidden.
            self.canvas.itemconfigure(
                self.play_item,
                state="hidden"
            )

            self.canvas.itemconfigure(
                self.do_not_item,
                state="hidden"
            )

            self.canvas.itemconfigure(
                self.confirm_cursor,
                state="hidden"
            )

        self.canvas.tag_raise(
            "chapter_select"
        )

    # ======================================================
    # STARTUP COMPLETION PROMPT
    # ======================================================

    def render_startup_prompt(self):

        # obj_screen_start exists on its own black screen.
        # Hide every normal Chapter Select element while it is active.
        for item in self.canvas_items:

            self.canvas.itemconfigure(
                item,
                state="hidden"
            )

        if self.startup_prompt_type == "continue":

            chapter = (
                self.startup_in_progress_chapter
            )

            prompt_text = (
                f"Continue from Chapter {chapter}?"
            )

            choices = [
                "Yes",
                "No",
            ]

        else:

            completed = (
                self.startup_completed_chapter
            )
            next_chapter = completed + 1

            prompt_text = (
                f"Chapter {completed} was completed."
            )

            choices = [
                f"Play Chapter {next_chapter}",
                "Chapter Select",
            ]

        # --------------------------------------------------
        # Prompt text
        # --------------------------------------------------

        prompt_color = self.color_with_alpha(
            WHITE,
            self.startup_alpha
        )

        prompt_image = self.main_font.render(
            prompt_text,
            color=prompt_color
        )

        self.startup_prompt_photo = (
            prompt_image
        )

        self.main_font_images[
            "startup_prompt"
        ] = prompt_image

        prompt_x, prompt_y = self.ui_to_screen(
            STARTUP_PROMPT_X,
            STARTUP_PROMPT_Y
            + self.startup_y_offset
        )

        self.canvas.coords(
            self.startup_prompt_text_item,
            prompt_x,
            prompt_y
        )

        self.canvas.itemconfigure(
            self.startup_prompt_text_item,
            image=prompt_image,
            state="normal"
        )

        # --------------------------------------------------
        # Choices
        # --------------------------------------------------

        self.startup_choice_photos = []
        selected_photo = None
        selected_y = STARTUP_CHOICE_START_Y

        for index, text in enumerate(choices):

            color = (
                YELLOW
                if index == self.startup_choice_index
                else WHITE
            )

            color = self.color_with_alpha(
                color,
                self.startup_alpha
            )

            image = self.main_font.render(
                text,
                color=color
            )

            self.startup_choice_photos.append(
                image
            )

            self.main_font_images[
                f"startup_choice_{index}"
            ] = image

            logical_y = (
                STARTUP_CHOICE_START_Y
                + (index * STARTUP_CHOICE_SPACING)
                + self.startup_y_offset
            )

            screen_x, screen_y = self.ui_to_screen(
                STARTUP_CHOICE_X,
                logical_y
            )

            self.canvas.coords(
                self.startup_choice_items[index],
                screen_x,
                screen_y
            )

            self.canvas.itemconfigure(
                self.startup_choice_items[index],
                image=image,
                state="normal"
            )

            if index == self.startup_choice_index:
                selected_photo = image
                selected_y = logical_y

        # --------------------------------------------------
        # Heart cursor
        #
        # Original centered-choice formula:
        #     320 - string_width(text) - 30
        # at 640x480, then halved for our logical viewport.
        # Using the rendered image width gives the same result
        # without hardcoding a separate X for each choice.
        # --------------------------------------------------

        if selected_photo is not None:

            logical_text_width = (
                selected_photo.width()
                / max(self.scale, 0.0001)
            )

            heart_x = (
                STARTUP_CHOICE_X
                - (logical_text_width / 2)
                - STARTUP_HEART_GAP
            )

            heart_y = (
                selected_y
                + STARTUP_HEART_Y_OFFSET
            )

            heart = self.heart_image.copy()

            alpha_channel = heart.getchannel(
                "A"
            )

            alpha_channel = alpha_channel.point(
                lambda value: round(
                    value
                    * max(
                        0.0,
                        min(1.0, self.startup_alpha)
                    )
                )
            )

            heart.putalpha(
                alpha_channel
            )

            heart = heart.resize(
                (
                    max(
                        1,
                        round(
                            heart.width
                            * self.scale
                        )
                    ),
                    max(
                        1,
                        round(
                            heart.height
                            * self.scale
                        )
                    )
                ),
                Image.Resampling.NEAREST
            )

            self.startup_heart_photo = (
                ImageTk.PhotoImage(heart)
            )

            screen_x, screen_y = self.ui_to_screen(
                heart_x,
                heart_y
            )

            self.canvas.coords(
                self.startup_cursor_item,
                screen_x,
                screen_y
            )

            self.canvas.itemconfigure(
                self.startup_cursor_item,
                image=self.startup_heart_photo,
                state="normal"
            )

        # --------------------------------------------------
        # Version display
        #
        # obj_ui_version is alpha-faded with the prompt, but
        # does not share the -40px slide. Its scale is half
        # the prompt/choice text at our logical resolution.
        # --------------------------------------------------

        version_color = self.color_with_alpha(
            GRAY,
            self.startup_alpha
        )

        version_image = self.main_font.render(
            "DELTARUNE v24",
            color=version_color,
            scale_multiplier=STARTUP_VERSION_SCALE
        )

        self.startup_version_photo = (
            version_image
        )

        self.main_font_images[
            "startup_version"
        ] = version_image

        version_x, version_y = self.ui_to_screen(
            STARTUP_VERSION_X,
            STARTUP_VERSION_Y
        )

        self.canvas.coords(
            self.startup_version_item,
            version_x,
            version_y
        )

        self.canvas.itemconfigure(
            self.startup_version_item,
            image=version_image,
            state="normal"
        )

        self.canvas.tag_raise(
            "startup_prompt"
        )

    # ======================================================
    # CHAPTER RENDERING
    # ======================================================

    def chapter_y(self, index):
        return CHAPTER_START_Y + (index * CHAPTER_SPACING)

    def render_chapters(self):

    # Clear old icon PhotoImage references.
        self.icon_images.clear()

        for i, chapter in enumerate(self.chapters):

            # --------------------------------------------------
            # Chapter row position
            # --------------------------------------------------

            y = (
                self.chapter_y(i)
                + self.entrance_y_offset
            )

            unlocked = chapter["unlocked"]

            # Chapters beyond the currently available chapter
            # count are displayed but cannot be selected.
            if i >= self.available_chapters:
                unlocked = False

            selected = (
                (
                    self.selection == "chapters"
                    and i == self.chapter_index
                )
                or
                (
                    self.selection == "confirm"
                    and self.selected_chapter is not None
                    and i == self.selected_chapter - 1
                )
            )

            # --------------------------------------------------
            # Colors
            # --------------------------------------------------

            if not unlocked:

                text_color = GRAY
                title_color = GRAY

            elif selected:

                text_color = YELLOW
                title_color = YELLOW

            else:

                text_color = WHITE
                title_color = WHITE
            # Apply the original _alpha fade.
            text_color = self.fade_color(
                text_color
            )

            title_color = self.fade_color(
                title_color
            )

            # --------------------------------------------------
            # Chapter text
            # --------------------------------------------------

            chapter_text = f"Chapter {chapter['number']}"

            if not unlocked:
                chapter_title = "- -"
            else:
                chapter_title = chapter["title"]

            # --------------------------------------------------
            # MainFont chapter number
            # --------------------------------------------------

            chapter_image = self.main_font.render(
                chapter_text,
                color=text_color
            )

            self.main_font_images[
                f"chapter_{i}"
            ] = chapter_image

            x_text, y_text = self.ui_to_screen(
                CHAPTER_TEXT_X,
                y
            )

            self.canvas.coords(
                self.chapter_text_items[i],
                x_text,
                y_text
            )

            self.canvas.itemconfigure(
                self.chapter_text_items[i],
                image=chapter_image
            )

            # --------------------------------------------------
            # MainFont chapter title
            # --------------------------------------------------

            title_image = self.main_font.render(
                chapter_title,
                color=title_color
            )

            self.main_font_images[
                f"title_{i}"
            ] = title_image

            x_title, y_title = self.ui_to_screen(
                CHAPTER_TITLE_X,
                y + CHAPTER_TITLE_Y_OFFSET
            )

            self.canvas.coords(
                self.chapter_title_items[i],
                x_title,
                y_title
            )

            self.canvas.itemconfigure(
                self.chapter_title_items[i],
                image=title_image,
                state = "normal"
            )

            # --------------------------------------------------
            # Icon
            # --------------------------------------------------

            icon_index = chapter["icon"]

            # Chapter 7 has no actual icon.
            if icon_index == 0:

                icon = self.create_blank_icon()

            else:

                # Chapter data is 1-based.
                icon_index -= 1

                if not (
                    0 <= icon_index
                    < len(self.chapter_icons)
                ):
                    continue

                icon = self.chapter_icons[icon_index]

                # Selected icons turn yellow, but only their
                # white portions are recolored. Black artwork
                # remains visible.
                if selected:

                    icon = self.colorize_icon(
                        icon,
                        YELLOW
                    )

                elif not unlocked:

                    icon = self.colorize_icon(
                        icon,
                        GRAY
                    )
                icon = self.apply_entrance_alpha(
                    icon
                )

            # --------------------------------------------------
            # Scale icon
            # --------------------------------------------------

            icon_scale = 1

            photo = ImageTk.PhotoImage(
                icon.resize(
                    (
                        round(
                            icon.width
                            * self.scale
                            * icon_scale
                        ),
                        round(
                            icon.height
                            * self.scale
                            * icon_scale
                        )
                    ),
                    Image.Resampling.NEAREST
                )
            )

            self.icon_images.append(photo)

            x_icon, y_icon = self.ui_to_screen(
                CHAPTER_ICON_X,
                y + CHAPTER_ICON_Y_OFFSET
            )

            self.canvas.coords(
                self.chapter_icon_items[i],
                x_icon,
                y_icon
            )

            self.canvas.itemconfigure(
                self.chapter_icon_items[i],
                image=photo,
                state = "normal"
            )

            # --------------------------------------------------
            # Horizontal divider
            # --------------------------------------------------

            self.canvas.itemconfigure(
            self.chapter_bar_items[i],
            fill=self.fade_color(DARK_GRAY)
            )

            bar_y = y + BAR_Y_OFFSET

            x1, y1 = self.ui_to_screen(
                BAR_X,
                bar_y
            )

            x2, y2 = self.ui_to_screen(
                BAR_X + BAR_WIDTH,
                bar_y + BAR_HEIGHT
            )

            self.canvas.coords(
                self.chapter_bar_items[i],
                x1,
                y1,
                x2,
                y2
            )

    # ======================================================
    # CHAPTER CONFIRMATION
    # ======================================================

    def render_confirmation(self):

        if self.selected_chapter is None:
            return

        chapter_index = self.selected_chapter - 1
        chapter = self.chapters[chapter_index]

        # --------------------------------------------------
        # Chapter number
        # --------------------------------------------------

        chapter_image = self.main_font.render(
            f"Chapter {chapter['number']}",
            color=self.fade_color(YELLOW)
        )

        self.main_font_images[
            "confirm_chapter"
        ] = chapter_image

        x, y = self.ui_to_screen(
            CHAPTER_TEXT_X,
            self.chapter_y(chapter_index)
            + self.entrance_y_offset
        )

        self.canvas.coords(
            self.chapter_text_items[chapter_index],
            x,
            y
        )

        self.canvas.itemconfigure(
            self.chapter_text_items[chapter_index],
            image=chapter_image,
            state="normal"
        )

        # --------------------------------------------------
        # Hide normal chapter title
        # --------------------------------------------------

        self.canvas.itemconfigure(
            self.chapter_title_items[chapter_index],
            state="hidden"
        )

        # --------------------------------------------------
        # Play / Do Not
        # --------------------------------------------------

        play_color = (
            YELLOW
            if self.confirm_index == 0
            else WHITE
        )

        do_not_color = (
            YELLOW
            if self.confirm_index == 1
            else WHITE
        )

        play_color = self.fade_color(
            play_color
        )

        do_not_color = self.fade_color(
            do_not_color
        )

        play_image = self.main_font.render(
            "Play",
            color=play_color
        )

        do_not_image = self.main_font.render(
            "Do Not",
            color=do_not_color
        )

        self.main_font_images[
            "confirm_play"
        ] = play_image

        self.main_font_images[
            "confirm_do_not"
        ] = do_not_image

        # Same vertical position as the chapter title.
        y = (
            self.chapter_y(chapter_index)
            + self.entrance_y_offset
            + CHAPTER_TITLE_Y_OFFSET
        )

        # --------------------------------------------------
        # Play
        # --------------------------------------------------

        x_play, y_play = self.ui_to_screen(
            CONFIRM_PLAY_X,
            y
        )

        self.canvas.coords(
            self.play_item,
            x_play,
            y_play
        )

        self.canvas.itemconfigure(
            self.play_item,
            image=play_image,
            state="normal"
        )

        # --------------------------------------------------
        # Do Not
        # --------------------------------------------------

        x_do_not, y_do_not = self.ui_to_screen(
            CONFIRM_DONOT_X,
            y
        )

        self.canvas.coords(
            self.do_not_item,
            x_do_not,
            y_do_not
        )

        self.canvas.itemconfigure(
            self.do_not_item,
            image=do_not_image,
            state="normal"
        )

        # --------------------------------------------------
        # Normal chapter cursor
        # --------------------------------------------------

        self.canvas.itemconfigure(
            self.cursor,
            state="hidden"
        )

        # --------------------------------------------------
        # Confirmation cursor
        # --------------------------------------------------

        cursor_x = (
            CONFIRM_HEART_X
            if self.confirm_index == 0
            else CONFIRM_DONOT_X - 25
        )

        cursor_y = (
            self.chapter_y(chapter_index)
            + self.entrance_y_offset
            + CONFIRM_Y_OFFSET
        )

        x_cursor, y_cursor = self.ui_to_screen(
            cursor_x,
            cursor_y
        )

        heart = self.apply_entrance_alpha(
            self.heart_image
        )

        heart = heart.resize(
            (
                round(
                    heart.width
                    * self.scale
                ),
                round(
                    heart.height
                    * self.scale
                )
            ),
            Image.Resampling.NEAREST
        )

        self.confirm_heart_photo = ImageTk.PhotoImage(
            heart
        )

        self.canvas.coords(
            self.confirm_cursor,
            x_cursor,
            y_cursor
        )

        self.canvas.itemconfigure(
            self.confirm_cursor,
            image=self.confirm_heart_photo,
            state="normal"
        )

    # ======================================================
    # ICON COLORING
    # ======================================================

    def create_blank_icon(self):
        """
        Creates the gray empty icon used for unavailable chapters.
        """

        # Native chapter icon size.
        width = 26
        height = 23

        image = Image.new(
            "RGBA",
            (width, height),
            (0, 0, 0, 0)
        )

        draw = ImageDraw.Draw(image)

        gray = (127, 127, 127, 255)

        # Outer frame
        draw.rectangle(
            (0, 0, width - 1, height - 1),
            outline=gray
        )

        # Inner frame
        draw.rectangle(
            (2, 2, width - 3, height - 3),
            outline=gray
        )

        return image

    def colorize_icon(self, image, color):

        """
        Recolor the white portions of a chapter icon while
        preserving the black details and transparent pixels.
        """

        image = image.copy()

        pixels = image.load()

        if color == YELLOW:
            rgb = (254, 254, 0)

        elif color == GRAY:
            rgb = (127, 127, 127)

        else:
            rgb = (254, 254, 254)

        for y in range(image.height):

            for x in range(image.width):

                r, g, b, a = pixels[x, y]

                if a == 0:
                    continue

                # Only recolor light/white pixels.
                # Dark pixels remain untouched.
                if r > 200 and g > 200 and b > 200:

                    pixels[x, y] = (
                        rgb[0],
                        rgb[1],
                        rgb[2],
                        a
                    )

        return image

    # ======================================================
    # STARS
    # ======================================================

    def render_stars(self):

        if not self.star_frames:
            return

        old_photos = self.star_photos
        new_photos = []

        for chapter_index, chapter in enumerate(
            self.chapters
        ):

            states = chapter.get(
                "completion_slots",
                [0, 0, 0]
            )

            for slot_index, item in enumerate(
                self.star_items[chapter_index]
            ):

                state = states[
                    slot_index
                ]

                # Make sure the state maps to a real frame.
                if not (
                    0 <= state
                    < len(self.star_frames)
                ):

                    state = 0

                star = (
                    self.star_frames[
                        state
                    ].copy()
                )

                # Same entrance fade as obj_ui_chapter.
                star = self.apply_entrance_alpha(
                    star
                )

                # Original sprite is from the 640x480 UI,
                # so halve its logical size for 320x240.
                star_scale = (
                    self.scale
                    * 0.5
                )

                star = star.resize(
                    (
                        max(
                            1,
                            round(
                                star.width
                                * star_scale
                            )
                        ),
                        max(
                            1,
                            round(
                                star.height
                                * star_scale
                            )
                        )
                    ),
                    Image.Resampling.NEAREST
                )

                photo = ImageTk.PhotoImage(
                    star
                )

                new_photos.append(
                    photo
                )

                x = CHAPTER_STAR_X

                y = (
                    self.chapter_y(
                        chapter_index
                    )
                    + self.entrance_y_offset
                    + CHAPTER_STAR_Y_OFFSET
                    + (
                        slot_index
                        * CHAPTER_STAR_SPACING
                    )
                )

                screen_x, screen_y = (
                    self.ui_to_screen(
                        x,
                        y
                    )
                )

                self.canvas.coords(
                    item,
                    screen_x,
                    screen_y
                )

                self.canvas.itemconfigure(
                    item,
                    image=photo,
                    state="normal"
                )

        self.star_photos = new_photos

    # ======================================================
    # FOOTER
    # ======================================================

    def render_footer(self):

        # --------------------------------------------------
        # Quit
        # --------------------------------------------------

        quit_color = (
            YELLOW
            if (
                self.selection == "footer"
                and self.footer_index == 0
            )
            else WHITE
        )

        quit_color = self.fade_color(
            quit_color
        )

        quit_image = self.main_font.render(
            "Quit",
            color=quit_color
        )

        self.main_font_images[
            "footer_quit"
        ] = quit_image

        # --------------------------------------------------
        # Japanese
        # --------------------------------------------------

        language_color = (
            YELLOW
            if (
                self.selection == "footer"
                and self.footer_index == 1
            )
            else WHITE
        )

        language_color = self.fade_color(
            language_color
        )

        language_image = self.main_font.render(
            "日本語",
            color=language_color
        )

        self.main_font_images[
            "footer_language"
        ] = language_image

        # --------------------------------------------------
        # Copyright / version information
        #
        # IMPORTANT:
        # This intentionally does NOT use entrance_alpha
        # or entrance_y_offset.
        #
        # This matches obj_ui_version being separate from
        # the footer's animated _choices array.
        # --------------------------------------------------

        info_image = self.main_font.render(
            "(C) Toby Fox 2018-2026\n"
            # "Exdwarf, Coolblubird\n"
            #   "2026-2027\n"
            "DELTARUNE v24",
            color=GRAY,
            scale_multiplier=FOOTER_INFO_SCALE
        )

        self.main_font_images[
            "footer_info"
        ] = info_image

        self.footer_info_photo = info_image

        # --------------------------------------------------
        # Copyright position -- stationary
        # --------------------------------------------------

        x_info, y_info = self.ui_to_screen(
            FOOTER_INFO_X,
            FOOTER_INFO_Y
        )

        self.canvas.coords(
            self.footer_info,
            x_info,
            y_info
        )

        self.canvas.itemconfigure(
            self.footer_info,
            image=self.footer_info_photo,
            state="normal"
        )

        # --------------------------------------------------
        # Animated footer position
        # --------------------------------------------------

        footer_y = (
            FOOTER_Y
            + self.entrance_y_offset
        )

        x_quit, y_quit = self.ui_to_screen(
            FOOTER_QUIT_X,
            footer_y
        )

        self.canvas.coords(
            self.quit_item,
            x_quit,
            y_quit
        )

        self.canvas.itemconfigure(
            self.quit_item,
            image=quit_image,
            state="normal"
        )

        x_language, y_language = self.ui_to_screen(
            FOOTER_LANGUAGE_X,
            footer_y
        )

        self.canvas.coords(
            self.language_item,
            x_language,
            y_language
        )

        self.canvas.itemconfigure(
            self.language_item,
            image=language_image,
            state="normal"
        )

    # ======================================================
    # CURSOR
    # ======================================================

    def render_cursor(self):

        if self.selection == "chapters":

            x = CURSOR_X

            y = (
                self.chapter_y(self.chapter_index)
                + CURSOR_Y_OFFSET
            )

        elif self.selection == "footer":

            x = (
                FOOTER_CURSOR_QUIT_X
                if self.footer_index == 0
                else FOOTER_CURSOR_LANGUAGE_X
            )

            y = FOOTER_Y + 1

        else:

            x = 130
            y = FOOTER_Y

        x_screen, y_screen = self.ui_to_screen(
            x,
            y
        )

        y += self.entrance_y_offset 

        heart_scale = self.scale

        heart = self.apply_entrance_alpha(
            self.heart_image
        )

        heart = heart.resize(
            (
                round(
                    self.heart_image.width
                    * heart_scale
                ),
                round(
                    self.heart_image.height
                    * heart_scale
                )
            ),
            Image.Resampling.NEAREST
        )

        self.heart_photo = ImageTk.PhotoImage(
            heart
        )

        self.canvas.coords(
            self.cursor,
            x_screen,
            y_screen
        )

        self.canvas.itemconfigure(
            self.cursor,
            image=self.heart_photo,
            state = "normal"
        ) 

    # ======================================================
    # INPUT
    # ======================================================

    def handle_input(self, key):

        # ==================================================
        # Startup completion prompt
        # ==================================================

        if self.startup_prompt_active:

            self.handle_startup_input(key)
            return

        # ==================================================
        # Confirmation screen
        # ==================================================

        if self.selection == "confirm":

            if key == "Left":

                self.confirm_index -= 1

                if self.confirm_index < 0:
                    self.confirm_index = 1

                self.audio.play_sfx(SND_MENUMOVE)
                self.render()

            elif key == "Right":

                self.confirm_index += 1

                if self.confirm_index > 1:
                    self.confirm_index = 0

                self.audio.play_sfx(SND_MENUMOVE)
                self.render()

            elif key == "z":

                self.confirm()

            elif key == "x":

                self.cancel_confirm()

            # Do NOT allow Up/Down or any other input
            # to reach the normal Chapter Select controls.
            return

        # ==================================================
        # Normal Chapter Select
        # ==================================================

        if key == "Up":

            self.move_up()

        elif key == "Down":

            self.move_down()

        elif key == "Left":

            self.move_left()

        elif key == "Right":

            self.move_right()

        elif key == "z":

            self.confirm()

        elif key == "x":

            self.back()

    def handle_startup_input(self, key):

        if not self.startup_input_enabled:
            return

        if key == "Up":

            self.startup_choice_index = (
                (self.startup_choice_index - 1) % 2
            )

            self.play_sfx(SND_MENUMOVE)
            self.render()

        elif key == "Down":

            self.startup_choice_index = (
                (self.startup_choice_index + 1) % 2
            )

            self.play_sfx(SND_MENUMOVE)
            self.render()

        elif key == "z":

            self.startup_input_enabled = False

            if self.startup_choice_index == 0:

                # YES on the Continue prompt resumes the unfinished
                # chapter. PLAY on the completion prompt launches
                # the next chapter. Both use the same launch
                # transition, just like obj_CHAPTER_SELECT.
                if self.startup_prompt_type == "continue":
                    target_chapter = (
                        self.startup_in_progress_chapter
                    )
                else:
                    target_chapter = (
                        self.startup_completed_chapter + 1
                    )

                self.selected_chapter = (
                    target_chapter
                )

                self.launch_chapter(
                    target_chapter
                )

            else:

                # NO / CHAPTER SELECT both enter the normal
                # Chapter Select state. snd_menuselect intentionally
                # stands in for the original snd_select.
                self.play_sfx(SND_MENUSELECT)
                self.start_normal_chapter_select(
                    from_startup_prompt=True
                )

    def start_normal_chapter_select(
        self,
        from_startup_prompt=False
    ):

        if self.startup_job is not None:

            try:
                self.root.after_cancel(
                    self.startup_job
                )
            except tk.TclError:
                pass

            self.startup_job = None

        self.startup_prompt_active = False
        self.startup_input_enabled = False

        for item in self.startup_items:

            self.canvas.itemconfigure(
                item,
                state="hidden"
            )

        self.selection = "chapters"
        self.footer_index = 0
        self.confirm_index = 0
        self.selected_chapter = None

        # When arriving here from obj_screen_start, the original
        # obj_screen_select.init() highlights the highest revealed
        # chapter. On an ordinary launch, preserve this Python
        # version's existing initial chapter_index behavior.
        if from_startup_prompt:

            highest_revealed = (
                self.progress.highest_revealed_chapter(
                    self.available_chapters
                )
            )

            self.chapter_index = max(
                0,
                min(
                    self.available_chapters - 1,
                    highest_revealed - 1
                )
            )

        # Start the drone only after the player reaches the normal
        # Chapter Select, matching change_state(Value_4).
        self.audio.play_music(
            "AUDIO_DRONE.ogg"
        )

        self.entrance_active = True
        self.entrance_alpha = 0.0
        self.entrance_y_offset = (
            ENTRANCE_START_Y_OFFSET
        )

        self.show()
        self.main_font.clear_cache()
        self.render()

        if self.entrance_job is not None:

            try:
                self.root.after_cancel(
                    self.entrance_job
                )
            except tk.TclError:
                pass

        self.entrance_job = self.root.after(
            ENTRANCE_FRAME_MS,
            self.update_entrance
        )

    # ======================================================
    # CHAPTER NAVIGATION
    # ======================================================

    def move_up(self):

        if self.selection == "chapters":

            if self.chapter_index > 0:

                self.chapter_index -= 1
                self.play_sfx(SND_MENUMOVE)

            else:

                # Top of list → footer.
                self.selection = "footer"
                self.footer_index = 0
                self.play_sfx(SND_MENUMOVE)

        elif self.selection == "footer":

            self.selection = "chapters"
            self.chapter_index = (
                self.available_chapters - 1
            )
            self.play_sfx(SND_MENUMOVE)

        self.render()

    def move_down(self):

        if self.selection == "chapters":

            if (
                self.chapter_index
                < self.available_chapters - 1
            ):

                self.chapter_index += 1
                self.play_sfx(SND_MENUMOVE)

            else:

                # Bottom → footer.
                self.selection = "footer"
                self.footer_index = 0
                self.play_sfx(SND_MENUMOVE)

        elif self.selection == "footer":

            self.selection = "chapters"
            self.chapter_index = 0
            self.play_sfx(SND_MENUMOVE)

        self.render()

    # ======================================================
    # FOOTER NAVIGATION
    # ======================================================

    def move_left(self):

        if self.selection == "confirm":

            self.confirm_index = 0
            self.play_sfx(SND_MENUMOVE)
            self.render()

            return

        if self.selection != "footer":
            return

        self.footer_index -= 1

        if self.footer_index < 0:
            self.footer_index = 1

        self.play_sfx(SND_MENUMOVE)
        self.render()

    def move_right(self):

        if self.selection == "confirm":

            self.confirm_index = 1
            self.play_sfx(SND_MENUMOVE)
            self.render()

            return

        if self.selection != "footer":
            return

        self.footer_index += 1

        if self.footer_index > 1:
            self.footer_index = 0

        self.play_sfx(SND_MENUMOVE)
        self.render()


    def confirm(self):

        # ==================================================
        # Chapter selection
        # ==================================================

        if self.selection == "chapters":

            chapter = self.chapters[
                self.chapter_index
            ]

            if not chapter["unlocked"]:
                return

            if chapter["number"] == 6:

                self.selected_chapter = 6

                self.confirm_index = 0

                self.selection = "confirm"

                self.play_sfx(SND_MENUSELECT)
                self.render()

            return

        # ==================================================
        # Confirmation
        # ==================================================

        if self.selection == "confirm":

            if self.confirm_index == 0:

                # PLAY (this chapter)
                self.launch_chapter(
                    self.selected_chapter
                )

            elif self.confirm_index == 1:

                # DO NOT (select this chapter)
                self.audio.play_sfx(SND_MENUSELECT)
                self.selection = "chapters"

                if self.selected_chapter is not None:

                    self.chapter_index = (
                        self.selected_chapter - 1
                    )

                self.render()

            return

        # ==================================================
        # Footer
        # ==================================================

        if self.selection == "footer":

            if self.footer_index == 0:

                # QUIT
                self.audio.stop_music()
                self.audio.play_sfx(SND_MENUSELECT)
                self.root.destroy()

            elif self.footer_index == 1:

                # Language selection later.
                pass

    def cancel_confirm(self):
        self.play_sfx(SND_SWING)
        self.selection = "chapters"

        if self.selected_chapter is not None:

            self.chapter_index = (
                self.selected_chapter - 1
            )

        self.confirm_index = 0

        self.render()

    def back(self):
        return

    # ======================================================
    # CHAPTER LAUNCH
    # ======================================================

    def launch_chapter(self, chapter):

        if chapter != 6:
            return

        if self.transitioning:
            return

        self.selected_chapter = 6
        self.transitioning = True

        # Stop the entrance animation from redrawing the live
        # Chapter Select underneath the transition.
        if self.entrance_job is not None:

            try:
                self.root.after_cancel(
                    self.entrance_job
                )
            except tk.TclError:
                pass

            self.entrance_job = None

        self.entrance_active = False

        # Stop the startup prompt's fade/slide animation too,
        # if Play Chapter 6 was selected from that screen.
        if self.startup_job is not None:

            try:
                self.root.after_cancel(
                    self.startup_job
                )
            except tk.TclError:
                pass

            self.startup_job = None

        # Give Tk a chance to finish drawing the confirmation
        # screen before we capture it.
        self.root.update_idletasks()

        # --------------------------------------------------
        # Capture the visible 320x240 Chapter Select viewport.
        #
        # This is the Tkinter equivalent of:
        #
        # sprite_create_from_surface(application_surface, ...)
        # --------------------------------------------------

        self.transition_source_image = (
            self.capture_chapter_select()
        )

        # --------------------------------------------------
        # Fade AUDIO_DRONE over 500 ms.
        #
        # AudioManager uses pygame for this project, so use
        # pygame.mixer.music.fadeout to match GameMaker's
        # audio_sound_gain(..., 0, 500) behavior.
        # --------------------------------------------------

        try:

            if pygame.mixer.music.get_busy():

                pygame.mixer.music.fadeout(
                    TRANSITION_BGM_FADE_MS
                )

            else:

                self.audio.stop_music()

        except pygame.error:

            # Fallback if the mixer music stream is not active.
            self.audio.stop_music()

        # --------------------------------------------------
        # Play the Chapter 6 confirmation sound and snd_menuselect
        # --------------------------------------------------
        self.play_sfx(SND_MENUSELECT)
        if CH6_SELECT.exists():

            self.chapter_confirm_sound = (
                pygame.mixer.Sound(
                    str(CH6_SELECT)
                )
            )

            self.chapter_confirm_channel = (
                self.chapter_confirm_sound.play()
            )

            self.transition_duration_ms = max(
                1,
                round(
                    self.chapter_confirm_sound.get_length()
                    * 1000
                )
            )

        else:

            # Keep the transition testable even if the WIP
            # sound has not been copied into the project yet.
            print(
                "Chapter Select warning: "
                f"{CH6_SELECT} was not found."
            )

            self.transition_duration_ms = 1000

        # --------------------------------------------------
        # Original obj_screen_transition starting values.
        # --------------------------------------------------

        self.transition_fadeout = 1.0
        self.transition_xscale = 1.0
        self.transition_yscale = 1.0
        self.transition_yy = UI_HEIGHT / 2

        self.transition_start_time = (
            time.perf_counter()
        )

        # Black background drawn above the live Chapter
        # Select. The captured image is then drawn above it.
        self.transition_black_item = (
            self.canvas.create_rectangle(
                0,
                0,
                self.canvas.winfo_width(),
                self.canvas.winfo_height(),
                fill=BLACK,
                outline="",
                tags=("chapter_transition",)
            )
        )

        center_x, center_y = self.ui_to_screen(
            UI_WIDTH / 2,
            UI_HEIGHT / 2
        )

        self.transition_image_item = (
            self.canvas.create_image(
                center_x,
                center_y,
                anchor="center",
                tags=("chapter_transition",)
            )
        )

        self.render_transition_frame()

        self.transition_job = self.root.after(
            TRANSITION_FRAME_MS,
            self.update_transition
        )

    def capture_chapter_select(self):
        """
        Capture the exact visible Chapter Select viewport as one
        RGBA image.

        IMPORTANT ON WINDOWS:
        Tk coordinates and ImageGrab coordinates are not always
        expressed in the same units when Windows display scaling
        (125%, 150%, etc.) is enabled. Using Tk's coordinates as
        ImageGrab pixels can therefore capture the wrong rectangle.

        We avoid that by grabbing the screen first, measuring the
        relationship between Tk screen units and physical screenshot
        pixels, then converting the viewport rectangle into the
        screenshot's pixel coordinate system before cropping it.

        This keeps the frozen image aligned with the live Chapter
        Select and prevents the footer from being cropped away.
        """

        # Make sure Tk has committed the current confirmation frame.
        self.root.update_idletasks()

        canvas_x = self.canvas.winfo_rootx()
        canvas_y = self.canvas.winfo_rooty()

        viewport_left = (
            canvas_x
            + self.offset_x
        )

        viewport_top = (
            canvas_y
            + self.offset_y
        )

        viewport_width = (
            UI_WIDTH
            * self.scale
        )

        viewport_height = (
            UI_HEIGHT
            * self.scale
        )

        # Grab first, crop second. This lets us compensate for
        # Windows DPI/display scaling rather than assuming Tk screen
        # coordinates are already physical pixels.
        screen_image = ImageGrab.grab().convert("RGBA")

        tk_screen_width = max(
            1,
            self.root.winfo_screenwidth()
        )

        tk_screen_height = max(
            1,
            self.root.winfo_screenheight()
        )

        grab_scale_x = (
            screen_image.width
            / tk_screen_width
        )

        grab_scale_y = (
            screen_image.height
            / tk_screen_height
        )

        left = round(
            viewport_left
            * grab_scale_x
        )

        top = round(
            viewport_top
            * grab_scale_y
        )

        right = round(
            (
                viewport_left
                + viewport_width
            )
            * grab_scale_x
        )

        bottom = round(
            (
                viewport_top
                + viewport_height
            )
            * grab_scale_y
        )

        # Keep the crop inside the grabbed screen. On the normal
        # fullscreen/primary-monitor setup these clamps should not
        # change anything, but they protect against rounding at the
        # screen edges.
        left = max(
            0,
            min(
                left,
                screen_image.width - 1
            )
        )

        top = max(
            0,
            min(
                top,
                screen_image.height - 1
            )
        )

        right = max(
            left + 1,
            min(
                right,
                screen_image.width
            )
        )

        bottom = max(
            top + 1,
            min(
                bottom,
                screen_image.height
            )
        )

        image = screen_image.crop(
            (
                left,
                top,
                right,
                bottom
            )
        )

        # Store the aftereffect at the game's logical 320x240
        # resolution, just like a GameMaker application_surface.
        image = image.resize(
            (
                UI_WIDTH,
                UI_HEIGHT
            ),
            Image.Resampling.NEAREST
        )

        return image

    def update_transition(self):

        if not self.transitioning:
            self.transition_job = None
            return

        # --------------------------------------------------
        # Original GameMaker Step:
        #
        # fadeout = lerp(fadeout, 0, 0.125);
        # xscale *= 0.95;
        # yscale *= 0.99;
        # yy *= 0.99;
        # --------------------------------------------------

        self.transition_fadeout += (
            0.0 - self.transition_fadeout
        ) * TRANSITION_ALPHA_LERP

        self.transition_xscale *= (
            TRANSITION_X_SCALE_MULTIPLIER
        )

        self.transition_yscale *= (
            TRANSITION_Y_SCALE_MULTIPLIER
        )

        self.transition_yy *= (
            TRANSITION_Y_MULTIPLIER
        )

        self.render_transition_frame()

        elapsed_ms = (
            time.perf_counter()
            - self.transition_start_time
        ) * 1000

        # GameMaker waits for a timer based on the length of
        # the chapter-confirm sound before launching.
        if (
            elapsed_ms
            >= self.transition_duration_ms
        ):

            self.finish_chapter_transition()
            return

        self.transition_job = self.root.after(
            TRANSITION_FRAME_MS,
            self.update_transition
        )

    def render_transition_frame(self):

        if (
            self.transition_source_image is None
            or self.transition_image_item is None
        ):
            return

        source = self.transition_source_image

        logical_width = max(
            1,
            round(
                source.width
                * self.transition_xscale
            )
        )

        logical_height = max(
            1,
            round(
                source.height
                * self.transition_yscale
            )
        )

        frame = source.resize(
            (
                logical_width,
                logical_height
            ),
            Image.Resampling.NEAREST
        )

        # draw_sprite_ext(..., alpha=fadeout)
        alpha = max(
            0.0,
            min(
                1.0,
                self.transition_fadeout
            )
        )

        alpha_channel = frame.getchannel(
            "A"
        )

        alpha_channel = alpha_channel.point(
            lambda value: round(
                value * alpha
            )
        )

        frame.putalpha(
            alpha_channel
        )

        # Apply the normal fullscreen viewport scale after
        # the logical GameMaker-style transform.
        screen_width = max(
            1,
            round(
                logical_width
                * self.scale
            )
        )

        screen_height = max(
            1,
            round(
                logical_height
                * self.scale
            )
        )

        frame = frame.resize(
            (
                screen_width,
                screen_height
            ),
            Image.Resampling.NEAREST
        )

        self.transition_photo = (
            ImageTk.PhotoImage(
                frame
            )
        )

        center_x, center_y = (
            self.ui_to_screen(
                UI_WIDTH / 2,
                self.transition_yy
            )
        )

        self.canvas.coords(
            self.transition_image_item,
            center_x,
            center_y
        )

        self.canvas.itemconfigure(
            self.transition_image_item,
            image=self.transition_photo
        )

        self.canvas.tag_raise(
            "chapter_transition"
        )

    def finish_chapter_transition(self):

        self.transition_job = None

        try:
            pygame.mixer.stop()
            pygame.mixer.music.stop()
        except pygame.error:
            pass

        self.audio.stop_music()

        # -----------------------------------------------
        # Leave Chapter Select as a completely black
        # fullscreen loading curtain.
        # -----------------------------------------------

        self.canvas.delete("all")
        self.canvas.configure(bg="black")

        self.root.update_idletasks()

        # -----------------------------------------------
        # Create a temporary "ready" file path.
        #
        # chapter6.py will create this file only after
        # Game has finished initializing and its first
        # intro frame is ready.
        # -----------------------------------------------

        fd, ready_path = tempfile.mkstemp(
            prefix="deltarune_ch6_ready_",
            suffix=".tmp",
        )

        os.close(fd)

        # Delete it immediately. We only wanted a unique path.
        try:
            os.remove(ready_path)
        except OSError:
            pass

        self.chapter_ready_file = ready_path

        # -----------------------------------------------
        # Launch Chapter 6.
        # -----------------------------------------------

        self.chapter_process = subprocess.Popen(
            [
                sys.executable,
                str(CHAPTER6_ENTRY),
                "--ready-file",
                ready_path,
            ],
            cwd=str(BASE_DIR),
        )

        # Keep THIS Tk mainloop alive while Chapter 6 loads.
        self.poll_chapter_ready()
    def destroy_after_handoff(self):
        if not self.handoff_pending:
            return

        self.handoff_pending = False

        try:
            self.root.destroy()
        except tk.TclError:
            pass
    def poll_chapter_ready(self):
        if self.chapter_ready_file is None:
            return
        # Chapter 6 says it is ready.
        if os.path.exists(self.chapter_ready_file):
            try:
                os.remove(self.chapter_ready_file)
            except OSError:
                pass

            self.chapter_ready_file = None
            self.handoff_job = None

            # NOW the black Chapter Select curtain can disappear.
            self.root.destroy()
            return

        # If Chapter 6 crashed before becoming ready, don't
        # leave the player trapped on a permanent black screen.
        if (
            self.chapter_process is not None
            and self.chapter_process.poll() is not None
        ):
            print(
                "Chapter 6 exited before signaling readiness. "
                f"Exit code: {self.chapter_process.returncode}"
            )

            self.root.destroy()
            return

        self.handoff_job = self.root.after(
            16,
            self.poll_chapter_ready,
        )

    # ======================================================
    # UPDATE
    # ======================================================

    def update_startup_prompt(self):

        if not self.startup_prompt_active:

            self.startup_job = None
            return

        # Original obj_screen_start Step:
        #
        # _alpha = lerp(_alpha, 1, 0.06);
        # _y_pos = lerp(_y_pos, 220, 0.14);
        # choice.y = lerp(choice.y, choice.ystart, 0.14);
        #
        # A single logical Y offset reproduces the same movement
        # for the prompt and both choices.
        self.startup_alpha += (
            1.0 - self.startup_alpha
        ) * STARTUP_ALPHA_LERP

        self.startup_y_offset += (
            0.0 - self.startup_y_offset
        ) * STARTUP_Y_LERP

        self.startup_timer += 1

        if (
            self.startup_timer
            >= STARTUP_INPUT_DELAY_STEPS
        ):
            self.startup_input_enabled = True

        animation_finished = (
            self.startup_alpha
            >= STARTUP_ALPHA_THRESHOLD
            and abs(self.startup_y_offset) < 0.01
        )

        if animation_finished:

            self.startup_alpha = 1.0
            self.startup_y_offset = 0.0

        # Avoid retaining every intermediate faded text color.
        self.main_font.clear_cache()
        self.render()

        if animation_finished:

            self.startup_job = None
            return

        self.startup_job = self.root.after(
            STARTUP_FRAME_MS,
            self.update_startup_prompt
        )

    def update_entrance(self):

        if not self.entrance_active:

            self.entrance_job = None
            return

        # --------------------------------------------------
        # Original GameMaker:
        #
        # _alpha = lerp(_alpha, 1, 0.06);
        # y = lerp(y, ystart, 0.14);
        # --------------------------------------------------

        self.entrance_alpha += (
            1.0 - self.entrance_alpha
        ) * ENTRANCE_ALPHA_LERP

        self.entrance_y_offset += (
            0.0 - self.entrance_y_offset
        ) * ENTRANCE_Y_LERP

        # Python floating point lerp will approach 1 forever,
        # so snap once it is visually indistinguishable.
        if (
            self.entrance_alpha
            >= ENTRANCE_ALPHA_THRESHOLD
        ):

            self.entrance_alpha = 1.0
            self.entrance_y_offset = 0.0
            self.entrance_active = False

        # During the animation MainFont would otherwise keep
        # every intermediate fade color in its cache.
        self.main_font.clear_cache()

        self.render()

        if self.entrance_active:

            self.entrance_job = self.root.after(
                ENTRANCE_FRAME_MS,
                self.update_entrance
            )

        else:

            self.entrance_job = None

    # ======================================================
    # ASSET UPDATE
    # ======================================================

    def update_assets(self):

        """
        Rebuilds assets when the game's scale changes.

        Canvas positions themselves are recalculated by
        render(), so the important part here is ensuring
        the cursor remains a valid PhotoImage.
        """

        pass