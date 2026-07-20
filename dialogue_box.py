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
        self.box_sprite = self.game.canvas.create_image(0, 300, image = self.box_photo, anchor="nw", state = "hidden", tags=("dialogue",))
        self.text_sprite = self.game.canvas.create_text(60, 335, anchor="nw", width=520, text="", fill="white",
                                                        font=("Determination Mono Web", 16), state = "hidden", tags=("dialogue",))
        soul_path = BASE_DIR/"sprites"/"player"/"player_red_soul.png"
        image = Image.open(soul_path)
        self.soul_photo=ImageTk.PhotoImage(image)
        self.soul_sprite = self.game.canvas.create_image(25,340,image=self.soul_photo,anchor="nw",state="hidden",tags=("dialogue",))
        self.game.canvas.coords(self.soul_sprite, 25, 340)
        current_y = 6
        self.game.canvas.coords(self.box_sprite, 0, current_y)
    def show(self):
        self.visible = True
        # self.game.canvas.tag_raise("dialogue")
        self.game.canvas.itemconfigure("dialogue", state = "normal")
    def hide(self):
        self.visible=False
        self.game.canvas.itemconfigure("dialogue", state="hidden")

    def set_text(self,text):
        self.game.canvas.itemconfigure(self.text_sprite, text=text)
    def render(self):
        dialogue_x = self.offset_x + 20*self.scale*self.camera_zoom
        dialogue_y = self.offset_y + 350*self.scale*self.camera_zoom