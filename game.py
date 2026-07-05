import tkinter as tk
from dialogue import Dialogue
from pathlib import Path
from rooms import bedroom
from PIL import Image, ImageTk
from player import Player
from dialogue_box import DialogueBox
BASE_DIR = Path(__file__).parent
class Game:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.create_widgets()
        self.bind_keys()
        self.load_dialogue()
        self.character_index = 0 
        self.typing = False 
        self.typing_job = None
        self.choice_active = False     
        self.load_room(bedroom)
        self.keys_pressed = set()
        self.player = Player(self, bedroom)
        self.update()
        self.typing = True
        self.type_text()
    def load_dialogue(self):
        self.dialogue_index = 0 
        self.dialogue_box = DialogueBox(self)
    def setup_window(self):
        self.root.title("Deltarune Chapter 6")
        self.root.geometry("640x480")
        self.root.configure(bg="black")
    def create_widgets(self):
        # self.canvas = tk.Canvas(self.root, width=640, height=480, highlightthickness=0, bd=0)
        self.canvas = tk.Canvas(self.root, width=640, height=480, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.background_sprite = None
        self.player_sprite = None
        self.background_label = tk.Label(self.root)
        self.background_label.place(x=0, y=0)
        self.player_label=tk.Label(self.root, bd=0)
        self.player_label.place(x=0,y=0)
        self.dialogue_frame = tk.Frame(self.root, bg="black", bd=4, relief="ridge")
        self.dialogue_label = tk.Label(self.root,font=("Times New Roman", 16),fg="white",bg="black",justify="left",anchor="nw")
        self.dialogue_label.pack(padx=15, pady=15, fill="both", expand=True)
        self.dialogue_label.place(x=20, y=350)
    def show_dialogue_box(self):
        self.dialogue_frame.place(x=10, y=340, width=600, height=130)
    def hide_dialogue_box(self):
        self.dialogue_frame.place_forget()
    def load_room(self,room):
        self.current_room = room
        image_path = BASE_DIR/"room_backgrounds"/room.background
        print(image_path)
        print(image_path.exists())
        image = Image.open(image_path)
        self.background_image= ImageTk.PhotoImage(image)
        self.background_label.config(image=self.background_image)
    def type_text(self):
        current = self.current_room.dialogue[self.dialogue_index]
        voice = current.voice
        text = current.text
        current_choices= current.choices
        scene_id = current.scene_id
        sound_effect = current.sound_effect
        if self.character_index == 0 and sound_effect:
            sound_effect.play()
        if self.character_index < len(text):
            self.dialogue_box.set_text(text[:self.character_index+1])
            if voice:
                voice.play()
            self.character_index +=1
            self.typing_job = self.root.after(50, self.type_text)
        else:
            self.typing = False
            self.typing_job = None
            if current_choices: #If the current dialogue has a choice,
                self.show_choices(current_choices)
    def advance_dialogue(self, event):
        if self.choice_active:
            return
        current = self.current_room.dialogue[self.dialogue_index]
        text = current.text
        if self.typing:
            self.dialogue_box.set_text(text)
            self.character_index = len(text)
            self.typing = False
            if self.typing_job is not None:
                self.root.after_cancel(self.typing_job)
                self.typing_job = None
            if current.choices: #If the current dialogue has a choice,
                self.show_choices(current.choices)
            return
        self.dialogue_index += 1
        if self.dialogue_index < len(self.current_room.dialogue):
            self.dialogue_box.set_text("")
            self.character_index = 0
            #self.typing = True
            #self.type_text()
    def start_dialogue(self):
        self.dialogue_box.show()
        self.dialogue_index = 0
        self.character_index = 0
        self.typing = True
        self.type_text()
    def bind_keys(self):
        self.root.bind("<KeyPress>", self.key_press)
        self.root.bind("<KeyRelease>", self.key_release)
        self.root.bind("<space>", self.advance_dialogue)
        self.root.bind("<z>", self.advance_dialogue)
        self.root.bind("<Z>", self.advance_dialogue)
    def key_press(self, event):
        self.keys_pressed.add(event.keysym)
    def key_release(self, event):
        self.keys_pressed.discard(event.keysym)
    def update(self):
        if not self.typing:
            isSprintHeld = "Shift_L" in self.keys_pressed
            if "Left" in self.keys_pressed:
                #self.player.move_left()
                self.player.move_left(isSprintHeld)
            if "Right" in self.keys_pressed:
                self.player.move_right()
            if "Up" in self.keys_pressed:
                self.player.move_up()
            if "Down" in self.keys_pressed:
                self.player.move_down()
        self.root.after(32, self.update)
    def run(self):
        self.root.mainloop()