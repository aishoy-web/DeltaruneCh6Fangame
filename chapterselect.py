from importlib.resources import path
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
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
FOOTER_INFO_Y = 214

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
CONFIRM_DONOT_X = 240
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

        self.star_photos = []
        self.chapters = []
        self.available_chapters = 6

        self.transitioning = False
        self.fade_alpha = 0

        # ==================================================
        # Chapter Select entrance animation
        # ==================================================

        self.entrance_active = True
        self.entrance_alpha = 0.0
        self.entrance_y_offset = ENTRANCE_START_Y_OFFSET
        self.entrance_job = None

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

        self.audio.play_music("AUDIO_DRONE.ogg")

        # First frame:
        # all animated elements are 20 logical pixels above
        # their normal positions and fully transparent.
        self.render()

        # Start the GameMaker-style fade/slide animation.
        self.entrance_job = self.root.after(
            ENTRANCE_FRAME_MS,
            self.update_entrance
        )

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

        # ----------------------------------------------
        # Temporary diagnostics
        # ----------------------------------------------

        # print("\n--- CHAPTER PROGRESS ---")

        # print(
        #     "Official save directory:",
        #     self.progress.official_dir
        # )

        # for chapter in self.chapters:

        #     print(
        #         f"Chapter {chapter['number']}:",
        #         "completion =",
        #         chapter["completion_slots"],
        #         "URA =",
        #         chapter["ura_results"]
        #     )

        # print(
        #     "Shadow grid:",
        #     self.shadow_crystal_grid
        # )

        # print("------------------------\n")
        # self.progress.debug_official_ini()

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

    def fade_color(self, color):
        """
        Simulate GameMaker draw alpha against the Chapter
        Select's black background.

        MainFont renders a fully opaque image, so fading its
        RGB values toward black produces the same visible result
        on this particular screen.
        """

        color = color.lstrip("#")

        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)

        alpha = max(
            0.0,
            min(1.0, self.entrance_alpha)
        )

        r = round(r * alpha)
        g = round(g * alpha)
        b = round(b * alpha)

        return f"#{r:02x}{g:02x}{b:02x}"


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

    # ======================================================
    # RENDER
    # ======================================================

    def render(self):

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
            else CONFIRM_DONOT_X - 5
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
            "Exdwarf, Coolblubird\n"
              "2026-2027\n"
            "DELTARUNE v23",
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

        if chapter == 6:
            self.selected_chapter = 6
            self.root.destroy()
            # A custom sound effect called "ch6_select" will be played here, but it hasn't been made yet.

    # ======================================================
    # UPDATE
    # ======================================================

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