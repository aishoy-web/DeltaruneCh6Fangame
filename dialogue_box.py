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
        self.box_label = tk.Label(game.root,image = self.box_photo, bd = 0)
        self.text_label = tk.Label(game.root, text="",bg="black", fg = "white", font = ("Determination Mono", 16), justify = "left", anchor = "nw")
        soul_path = BASE_DIR/"sprites"/"player"/"player_red_soul.png"
        image = Image.open(soul_path)
        self.soul_photo=ImageTk.PhotoImage(image)
        self.soul_label=tk.Label(game.root,image=self.soul_photo,bd=0)
    def show(self):
        self.visible = True
        self.box_label.place(x=0,y=300)
        self.text_label.place(x=60,y=335)
    def hide(self):
        self.visible=False
        self.box_label.place_forget()
        self.text_label.place_forget()
        self.soul_label.place_forget()
    def set_text(self,text):
        self.text_label.config(text=text)