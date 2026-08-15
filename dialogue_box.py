import tkinter as tk
from PIL import Image, ImageTk
class DialogueBox:
    def __init__(self, game):
        self.game = game
        # Dialogue state
        self.visible = False
        self.cursor_visible = False
        self.portrait = None
        self.portrait_sprite = None
        self.portrait_photo = None
        self.portrait_width = 65
        self.text_padding = 12
        self.portrait_gap = 8
        # Box dimensions
        self.box_x = 10
        self.box_y = 6
        self.box_width = 300
        self.box_height = 80
        # Text settings
        # self.text_x = 160
        # self.text_y = 46
        self.text_width = 270
        # Canvas items
        self.canvas_items = []
        self.box_sprite = None
        self.text_sprite = None
        self.soul_sprite = None
        # Soul cursor
        soul_path = (
            "sprites/player/player_red_soul/spr_heart_0.png")

        image = Image.open(soul_path)
        self.soul_photo = ImageTk.PhotoImage(image)
    def create_widgets(self):
        # Dialogue background
        self.box_sprite = self.game.canvas.create_rectangle(
            0, 0, 0, 0,
            fill="black",
            outline="white",
            width=9,
            state="hidden",
            tags=("dialogue",)
        )
        # Dialogue text
        self.text_sprite = self.game.canvas.create_text(
            0,
            0,
            anchor="nw",
            width=260,
            text="",
            fill="white",
            font=("Determination Mono Web", 45),
            state="hidden",
            tags=("dialogue",)
        )
        # Soul cursor
        self.soul_sprite = self.game.canvas.create_image(
            0, 0,
            image=self.soul_photo,
            anchor="center",
            state="hidden",
            tags=("dialogue_cursor",))
        self.canvas_items.extend([
            self.box_sprite,
            self.text_sprite,
            self.soul_sprite])

    def layout_widgets(self):
        # -------------------------
        # Dialogue box
        # -------------------------
        box_x1, box_y1 = self.game.ui_to_screen(
            self.box_x,
            self.box_y
        )

        box_x2, box_y2 = self.game.ui_to_screen(
            self.box_x + self.box_width,
            self.box_y + self.box_height
        )

        self.game.canvas.coords(
            self.box_sprite,
            box_x1,
            box_y1,
            box_x2,
            box_y2
        )

        # -------------------------
        # Text position
        # -------------------------
        if self.portrait is None:
            # Text starts near the upper-left of the box
            text_x = self.box_x + self.text_padding
            text_width = self.box_width - self.text_padding * 2

        else:
            # Leave room for the portrait
            text_x = (
                self.box_x
                + self.text_padding
                + self.portrait_width
                + self.portrait_gap
            )

            text_width = (
                self.box_width
                - self.portrait_width
                - self.text_padding * 2
                - self.portrait_gap
            )

        # Text should start near the top of the box
        text_y = self.box_y + self.text_padding

        text_x, text_y = self.game.ui_to_screen(
            text_x,
            text_y
        )

        self.game.canvas.coords(
            self.text_sprite,
            text_x,
            text_y
        )

        self.game.canvas.itemconfigure(
            self.text_sprite,
            width=text_width * self.game.scale,
            anchor="nw"
        )

        # -------------------------
        # Soul cursor
        # -------------------------
        soul_x, soul_y = self.game.ui_to_screen(
            25,
            self.box_y + 40
        )

        self.game.canvas.coords(
            self.soul_sprite,
            soul_x,
            soul_y
        )
    def show(self):
        self.visible = True
        self.game.canvas.itemconfigure(
            self.box_sprite,
            state="normal")
        self.game.canvas.itemconfigure(
            self.text_sprite,
            state="normal")
        self.hide_cursor()
        self.game.canvas.tag_raise("dialogue")
    def hide(self):
        self.visible = False
        self.game.canvas.itemconfigure(
            self.box_sprite,
            state="hidden")
        
        self.game.canvas.itemconfigure(
            self.text_sprite,
            state="hidden")
        
        self.hide_cursor()
    def set_text(self, text):
        self.game.canvas.itemconfigure(
            self.text_sprite,
            text=text)
        
    def show_cursor(self):
        self.cursor_visible = True
        self.game.canvas.itemconfigure(
            self.soul_sprite,
            state="normal")
        self.game.canvas.tag_raise("dialogue_cursor")
    def hide_cursor(self):
        self.cursor_visible = False
        self.game.canvas.itemconfigure(
            self.soul_sprite,
            state="hidden")
    def update_position(self):
        player_center_y = (
            self.game.player.y +
            self.game.player.animation.sprite_height / 2
        )

        viewport_y = player_center_y - self.game.camera_y

        if viewport_y >= self.game.viewport_height / 2:
            self.box_y = 6
        else:
            self.box_y = 154
    # def set_portrait(self):
    #     self.portrait = image
    def clear_portrait(self):
        self.portrait = None
    def render_static(self):
        if not self.canvas_items:
            self.create_widgets()
        if self.visible:
            self.update_position()
        self.layout_widgets()