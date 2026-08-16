from pathlib import Path
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).resolve().parent
cursor_path = (
    BASE_DIR
    / "sprites"
    / "player"
    / "player_red_soul"
    / "spr_heart_0.png"
)


class Menu:
    def __init__(self, game):
        self.game = game

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
        #
        # These coordinates were calibrated against
        # DELTARUNE's menu.
        #
        self.menu_x = 17
        self.menu_y = 85.5

        # --------------------------------
        # Soul cursor
        # --------------------------------

        self.soul_scale = 0.5

        self.cursor_image = Image.open(cursor_path)
        self.cursor_photo = None

        self.refresh_cursor()

    def refresh_cursor(self):
        """Scale the soul cursor according to the game's current scale."""

        scale = self.game.scale

        cursor_width = max(
            1,
            int(self.cursor_image.width * scale * self.soul_scale)
        )

        cursor_height = max(
            1,
            int(self.cursor_image.height * scale * self.soul_scale)
        )

        cursor_scaled = self.cursor_image.resize(
            (cursor_width, cursor_height),
            Image.Resampling.NEAREST
        )

        self.cursor_photo = ImageTk.PhotoImage(cursor_scaled)

        if self.cursor is not None:
            self.game.canvas.itemconfigure(
                self.cursor,
                image=self.cursor_photo
            )

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
                font=("Determination Mono Web", 45),
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

    def open(self):
        self.visible = True

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

    def move_up(self):
        if self.selected > 0:
            self.selected -= 1
            self.render_dynamic()

    def move_down(self):
        if self.selected < len(self.options) - 1:
            self.selected += 1
            self.render_dynamic()

    def render_static(self):
        if not self.canvas_items:
            self.create_widgets()

        # The menu box is scaled by UISpriteSheet.
        # The cursor is scaled separately because it is
        # currently a player sprite rather than a UI sprite.
        self.refresh_cursor()

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