import pygame
from pathlib import Path
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).resolve().parent

cursor_path = (
    BASE_DIR
    / "sprites"
    / "player"
    / "player_red_soul"
    / "spr_heartsmall.png"
)


class Menu:
    def __init__(self, game):
        self.game = game
        self.menu_move = pygame.mixer.Sound(
            BASE_DIR/
            "sfx"/
            "snd_menumove.wav"
        )
        self.menu_select = pygame.mixer.Sound(
            BASE_DIR/
            "sfx"/
            "snd_menuselect.wav"
        )
        # Canvas items
        self.canvas_items = []
        self.option_text = []

        self.menu_sprite = None
        self.cursor = None

        # Menu state
        self.visible = False
        self.selected = 0

        self.options = [
            "ITEM",
            "STAT",
            "CELL"
        ]

        # --------------------------------
        # Menu position
        # --------------------------------

        self.menu_x = 16
        self.menu_y = 84

        # --------------------------------
        # Soul cursor
        # --------------------------------

        self.soul_scale = 1

        self.cursor_image = Image.open(
            cursor_path
        ).convert("RGBA")

        self.cursor_photo = None

        self.refresh_cursor()

    # ======================================================
    # CURSOR
    # ======================================================

    def refresh_cursor(self):
        """
        Scale the soul cursor according to the current
        game scale.
        """

        scale = float(self.game.scale)

        cursor_width = max(
            1,
            round(
                self.cursor_image.width
                * scale
                * self.soul_scale
            )
        )

        cursor_height = max(
            1,
            round(
                self.cursor_image.height
                * scale
                * self.soul_scale
            )
        )

        cursor_scaled = self.cursor_image.resize(
            (
                cursor_width,
                cursor_height
            ),
            Image.Resampling.NEAREST
        )

        self.cursor_photo = ImageTk.PhotoImage(
            cursor_scaled
        )

        # If the Canvas item already exists,
        # immediately replace its image.
        if self.cursor is not None:
            self.game.canvas.itemconfigure(
                self.cursor,
                image=self.cursor_photo
            )

    # ======================================================
    # WIDGET CREATION
    # ======================================================

    def create_widgets(self):

        # --------------------------------
        # Menu box
        # --------------------------------

        self.menu_sprite = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.game.ui_sprites.get("menu_box"),
            state="hidden",
            tags=("menu",)
        )

        # --------------------------------
        # Soul cursor
        # --------------------------------

        self.cursor = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.cursor_photo,
            state="hidden",
            tags=("menu",)
        )

        # --------------------------------
        # Menu options
        # --------------------------------

        for option in self.options:
            text = self.game.canvas.create_text(
                0,
                0,
                text=option,
                anchor="nw",
                font=(
                    "Determination Mono Web",
                    45
                ),
                fill="white",
                state="hidden",
                tags=("menu",)
            )

            self.option_text.append(text)

        self.canvas_items.extend([
            self.menu_sprite,
            self.cursor,
            *self.option_text
        ])

    # ======================================================
    # LAYOUT
    # ======================================================

    def layout_widgets(self):

        # --------------------------------
        # Menu box
        # --------------------------------

        x, y = self.game.ui_to_screen(
            self.menu_x,
            self.menu_y
        )

        self.game.canvas.coords(
            self.menu_sprite,
            x,
            y
        )

        # --------------------------------
        # Menu options
        # --------------------------------

        for i, text in enumerate(self.option_text):

            x, y = self.game.ui_to_screen(
                41,
                94 + i * 18
            )

            self.game.canvas.coords(
                text,
                x,
                y
            )

    # ======================================================
    # OPEN / CLOSE
    # ======================================================

    def open(self):
        self.visible = True
        self.menu_move.play()
        self.render_static()
        self.render_dynamic()

        for item in self.canvas_items:
            self.game.canvas.itemconfigure(
                item,
                state="normal"
            )

        self.game.canvas.tag_raise("menu")

    def close(self):
        self.visible = False

        for item in self.canvas_items:
            self.game.canvas.itemconfigure(
                item,
                state="hidden"
            )

    # ======================================================
    # SELECTION
    # ======================================================

    def move_up(self):
        if self.selected > 0:
            self.selected -= 1
            self.menu_move.play()
            self.render_dynamic()

    def move_down(self):
        if self.selected < len(self.options) - 1:
            self.selected += 1
            self.menu_move.play()
            self.render_dynamic()

    # ======================================================
    # RENDERING
    # ======================================================

    def render_static(self):

        if not self.canvas_items:
            self.create_widgets()

        # --------------------------------
        # Refresh menu sprite
        # --------------------------------
        #
        # This is the important part.
        #
        # UISpriteSheet.get() uses the CURRENT
        # game.scale, so the menu box is replaced
        # whenever the game is fullscreen-scaled.
        # --------------------------------

        menu_photo = self.game.ui_sprites.get(
            "menu_box"
        )

        self.game.canvas.itemconfigure(
            self.menu_sprite,
            image=menu_photo
        )

        # --------------------------------
        # Refresh cursor
        # --------------------------------

        self.refresh_cursor()

        # --------------------------------
        # Refresh text
        # --------------------------------

        # self.refresh_text_scale()

        # --------------------------------
        # Position everything
        # --------------------------------

        self.layout_widgets()

    def render_dynamic(self):

        if self.cursor is None:
            return

        # --------------------------------
        # Soul cursor
        # --------------------------------

        cursor_y = 98 + self.selected * 18

        x, y = self.game.ui_to_screen(
            28,
            cursor_y
        )

        self.game.canvas.coords(
            self.cursor,
            x,
            y
        )

        self.game.canvas.tag_raise("menu")