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
        self.box_sprite = None
        self.text_sprite = None
        self.soul_sprite = None
        soul_path = BASE_DIR/"sprites"/"player"/"player_red_soul"/"spr_heart_0.png"
        image = Image.open(soul_path)
        self.soul_photo=ImageTk.PhotoImage(image)
        self.game.canvas.coords(self.soul_sprite, 25, 340)
        current_y = 6
        self.game.canvas.coords(self.box_sprite, 0, current_y)
    def create_widgets(self):
        self.box_sprite = self.game.canvas.create_image(
            0, 0,
            image=self.box_photo,
            anchor="nw",
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
        box_x, box_y = self.game.ui_to_screen(0, 6)
        self.game.canvas.coords(self.box_sprite, box_x, box_y)

        text_x, text_y = self.game.ui_to_screen(60, 35)
        self.game.canvas.coords(self.text_sprite, text_x, text_y)

        soul_x, soul_y = self.game.ui_to_screen(25, 40)
        self.game.canvas.coords(self.soul_sprite, soul_x, soul_y)
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