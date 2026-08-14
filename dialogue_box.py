from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk
BASE_DIR = Path(__file__).parent
class DialogueBox:
    def __init__(self, game):
        self.game = game
        self.visible = False
        box_path = BASE_DIR/"sprites"/"player"/"dialogue_box_ut.png"
        image = Image.open(box_path)
        self.box_photo = ImageTk.PhotoImage(image)
        self.canvas_items = []
        self.box_x = 0
        self.box_y = self.game.viewport_width
        self.box_width = 320
        self.box_height = 74
        self.box_sprite = None
        self.text_sprite = None
        self.soul_sprite = None
        soul_path = BASE_DIR/"sprites"/"player"/"player_red_soul"/"spr_heart_0.png"
        image = Image.open(soul_path)
        self.soul_photo=ImageTk.PhotoImage(image)
        # self.game.canvas.coords(self.soul_sprite, 25, 340)
        # current_y = 6
        # self.game.canvas.coords(self.box_sprite, 0, current_y)
    def create_widgets(self):
        self.box_sprite = self.game.canvas.create_rectangle(
            0, 0, 0, 0,
            fill = "black",
            outline="white",
            width = 9,
            state="hidden",
            tags=("dialogue",)
        )

        self.text_sprite = self.game.canvas.create_text(
            0, 0,
            anchor="nw",
            width=260,
            text="",
            fill="white",
            font=("Determination Mono Web", 16),
            state="hidden",
            tags=("dialogue",)
        )

        self.soul_sprite = self.game.canvas.create_image(
            0, 0,
            image=self.soul_photo,
            anchor="nw",
            state="hidden",
            tags=("dialogue",)
        )
        self.canvas_items.append(self.box_sprite)
        self.canvas_items.append(self.text_sprite)
        self.canvas_items.append(self.soul_sprite)
    def layout_widgets(self):
        x1, y1 = self.game.ui_to_screen(
            self.box_x,
            self.box_y
        )

        x2, y2 = self.game.ui_to_screen(
            self.box_x + self.box_width,
            self.box_y + self.box_height
        )

        self.game.canvas.coords(
            self.box_sprite,
            x1, y1,
            x2, y2
        )
    def show(self):
        self.visible = True
        # self.game.canvas.tag_raise("dialogue")
        self.game.canvas.itemconfigure("dialogue", state = "normal")
    def hide(self):
        self.visible=False
        self.game.canvas.itemconfigure("dialogue", state="hidden")

    def set_text(self,text):
        self.game.canvas.itemconfigure(self.text_sprite, text=text)
    def render_static(self):
        if not self.canvas_items:
            self.create_widgets()
        self.layout_widgets()