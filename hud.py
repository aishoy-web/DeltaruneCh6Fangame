class HUD:
    def __init__(self, game):
        self.game = game

        # Status box dimensions in native UI pixels
        self.status_x = 16
        self.status_y = 161.5

        self.status_width = 71
        self.status_height = 55

        # Text positioning
        self.text_padding = 7

        # Canvas items
        self.canvas_items = []
        self.status_sprite = None
        self.status_text = None

        # Player information
        self.level = 1
        self.hp = 20
        self.max_hp = 20
        self.money = 2

        self.create_widgets()

    def create_widgets(self):

        # --------------------------------
        # Status box
        # --------------------------------

        self.status_sprite = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.game.ui_sprites.get("status_box"),
            state="hidden",
            tags=("hud",)
        )

        # --------------------------------
        # Status text
        # --------------------------------

        self.status_text = self.game.canvas.create_text(
            0,
            0,
            anchor="nw",
            text="",
            fill="white",
            font=("Determination Mono Web", 18),
            state="hidden",
            tags=("hud",)
        )

        self.canvas_items.extend([
            self.status_sprite,
            self.status_text
        ])

        self.update_text()

    def update_text(self):
        text = (
            f"Kris\n"
            f"LV {self.level}\n"
            f"HP {self.hp}/{self.max_hp}\n"
            f"$ {self.money}"
        )

        self.game.canvas.itemconfigure(
            self.status_text,
            text=text
        )

    def update_position(self):
        player_center_y = (
            self.game.player.y +
            self.game.player.animation.sprite_height / 2
        )

        viewport_y = (
            player_center_y -
            self.game.camera_y
        )

        # Move to the bottom when Kris is in the bottom 40%
        if viewport_y <= self.game.viewport_height * 0.6:
            # self.status_y = 26
            new_y = 26
        else:
            # self.status_y = 161
            new_y = 161
        if new_y != self.status_y:
            self.status_y = new_y
            self.layout_widgets()


    def layout_widgets(self):

        # --------------------------------
        # Status box
        # --------------------------------

        x, y = self.game.ui_to_screen(
            self.status_x,
            self.status_y
        )

        self.game.canvas.coords(
            self.status_sprite,
            x,
            y
        )

        # --------------------------------
        # Status text
        # --------------------------------

        text_x = self.status_x + self.text_padding
        text_y = self.status_y + self.text_padding

        text_x, text_y = self.game.ui_to_screen(
            text_x,
            text_y
        )

        self.game.canvas.coords(
            self.status_text,
            text_x,
            text_y
        )

    def render_static(self):

        # --------------------------------
        # Refresh the scaled status sprite
        # --------------------------------

        status_photo = self.game.ui_sprites.get(
            "status_box"
        )

        self.game.canvas.itemconfigure(
            self.status_sprite,
            image=status_photo
        )

        # --------------------------------
        # Position HUD
        # --------------------------------

        self.layout_widgets()

        self.game.canvas.tag_raise("hud")

    def open(self):
        self.game.canvas.itemconfigure(
            self.status_sprite,
            state="normal"
        )

        self.game.canvas.itemconfigure(
            self.status_text,
            state="normal"
        )

        self.game.canvas.tag_raise("hud")

    def close(self):
        self.game.canvas.itemconfigure(
            self.status_sprite,
            state="hidden"
        )

        self.game.canvas.itemconfigure(
            self.status_text,
            state="hidden"
        )