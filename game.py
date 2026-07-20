import tkinter as tk
from dialogue import Dialogue
from pathlib import Path
from rooms import bedroom, ROOMS
from PIL import Image, ImageTk
from player import Player
from dialogue_box import DialogueBox
from room import Exit
from room import Room
import json
BASE_DIR = Path(__file__).parent
# with open(BASE_DIR/"eng.json",encoding="utf-8") as f:
#     Dialogue = json.load(f)
class Game:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        # Rendering state
        self.scale = 1.0
        self.camera_zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.create_widgets()
        self.bind_keys()
        self.load_dialogue()
        self.character_index = 0
        self.typing = False
        self.typing_job = None
        self.choice_active = False
        self.collision_debug = []
        self.debug_mode = True # Set to True to view player coordinates and collision hitboxes for player and collision
        self.keys_pressed = set()
        # Load assets
        self.load_room("myroom")
        # Create game objects
        self.player = Player(self)
        # Draw everything once
        self.render()
        self.update_debug_hud()
        self.update()
        self.typing = True
        with open(BASE_DIR / "eng.json", encoding="utf-8") as f:
            self.dialogue_data = json.load(f)
        self.type_text()
        # print(self.root.pack_slaves())
    def load_dialogue(self):
        self.dialogue_index = 0 
        self.dialogue_box = DialogueBox(self)
    def setup_window(self):
        self.root.title("Deltarune Chapter 6")
        self.root.geometry("320x240")
        self.root.configure(bg="black")
        self.fullscreen = False
        self.root.bind("<F11>",self.toggle_fullscreen)
        self.root.bind("<Escape>",self.exit_fullscreen)
        self.root.bind("<Configure>", self.window_resized)
    def toggle_fullscreen(self, event = None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        self.root.after(50,self.on_resize)
    def exit_fullscreen(self, event = None):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)
        self.on_resize()
    def window_resized(self, event):
        if event.widget != self.root:
            return
    def game_to_screen(self,x,y):
        return (self.offset_x+x*self.scale, self.offset_y+y*self.scale)
    def update_scale(self):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < 2 or height < 2:
            return

        self.scale = min(
            width / self.game_width,
            height / self.game_height)

        self.offset_x = (width - self.game_width * self.scale) / 2
        self.offset_y = (height - self.game_height * self.scale) / 2
    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, width=640, height=480, highlightthickness=0, bd=0, bg = "black")
        self.canvas.pack(fill="both", expand=True)
        self.debug_text = self.canvas.create_text(
            5,
            5,
            anchor="nw",
            fill="white",
            font=("Determination Mono Web", 20),
            text="",
        )
        self.background_sprite = None
        self.player_sprite = None
        # print("Children of root:")
        # for child in self.root.winfo_children():
            # print(type(child), child)
    def load_room(self, room_id):
        room = ROOMS[room_id]
        self.room = room
        background_path = BASE_DIR/"room_backgrounds"/room.background

        # print(f"Loaded room: {room.name}") #Debug for room loading, keep this commented out unless testing room loading.

        self.background_pil = Image.open(background_path)
        self.game_width = self.background_pil.width
        self.game_height = self.background_pil.height
        # print(self.background_pil.size)
        self.on_resize()
        self.background_image = ImageTk.PhotoImage(self.background_pil)
        if self.background_sprite is None:
            self.background_sprite = self.canvas.create_image(0,0, image = self.background_image, anchor = "nw")
        else: 
            self.canvas.itemconfig(self.background_sprite, image=self.background_image)
        self.canvas.delete("debug")
        
        for rect in self.collision_debug:
            self.canvas.delete(rect)
        self.collision_debug.clear()
        
        if hasattr(self, "player"):
            self.canvas.tag_raise(self.player.sprite)
            self.player.room = room
    def check_room_transitions(self):
        for exit in self.room.exits:
            if self.player.is_touching_exit(exit):
                self.change_room(exit)
                break
    def change_room(self,exit):
        self.load_room(exit.destination)
        self.player.x = exit.spawn_x
        self.player.y = exit.spawn_y
        self.render()
    def on_resize(self,event = None):
        # Ignore tiny events while the window is initializing
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 2 or canvas_height < 2:
            return
        self.scale = min(canvas_width/self.game_width, canvas_height/self.game_height)
        draw_width = int(self.game_width * self.scale)
        draw_height = int(self.game_height * self.scale)
        self.offset_x = (canvas_width - draw_width) // 2
        self.offset_y = (canvas_height - draw_height) // 2
        self.update_scale()
        self.render()
    def render(self):
        self.update_scale()        # Game updates scale
        self.render_background()

        if hasattr(self, "player"):
            self.player.render()

        self.render_debug()
    def rectangles_overlap(a,b):
        left1, top1, right1, bottom1 = a
        left2, top2, right2, bottom2 = b
        return (
            right1 > left2 and
            left1 < right2 and
            bottom1 > top2 and
            top1 < bottom2)
    def render_debug(self):
        self.canvas.delete("debug")
        self.collision_debug.clear()
        if not self.debug_mode:
            return
        for left, top, right, bottom in self.room.collisions:
            rect = self.canvas.create_rectangle(
                left * self.scale + self.offset_x,
                top * self.scale + self.offset_y,
                right * self.scale + self.offset_x,
                bottom * self.scale + self.offset_y,
                outline="red",
                width=2,
                tags="debug")
            self.collision_debug.append(rect)
        for exit in self.room.exits:
            left = exit.x
            top = exit.y
            right = exit.x + exit.width
            bottom = exit.y + exit.height

            rect = self.canvas.create_rectangle(
                left * self.scale + self.offset_x,
                top * self.scale + self.offset_y,
                right * self.scale + self.offset_x,
                bottom * self.scale + self.offset_y,
                outline="green",
                width=2,
                tags="debug",)
            self.collision_debug.append(rect)
    def update_debug_hud(self):
        if not self.debug_mode:
            self.canvas.itemconfigure(self.debug_text, state="hidden")
            return
        self.canvas.itemconfigure(self.debug_text, state="normal")
        self.canvas.itemconfig(
            self.debug_text,
            text=(
                f"Room: {self.room.name}\n"
                f"X: {self.player.x:.1f}\n"
                f"Y: {self.player.y:.1f}"))
    def render_background(self):
        scaled = self.background_pil.resize((int(self.game_width*self.scale),int(self.game_height*self.scale)),Image.Resampling.NEAREST)
        self.background_image = ImageTk.PhotoImage(scaled)
        if self.background_sprite is None:
            self.background_sprite = self.canvas.create_image(
            self.offset_x,
            self.offset_y,
            image=self.background_image,
            anchor="nw")
        else:
            self.canvas.itemconfig(
            self.background_sprite,
            image=self.background_image)

            self.canvas.coords(
                self.background_sprite,
                self.offset_x,
                self.offset_y)
    def type_text(self):
        current = self.room.dialogue[self.dialogue_index]
        voice = current.voice
        text = self.dialogue_data.get(current.text_id,current.text_id)
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
        current = self.room.dialogue[self.dialogue_index]
        text = current.text_id
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
        if self.dialogue_index < len(self.room.dialogue):
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
        self.root.bind("<Configure>", self.on_resize)
    def key_press(self, event):
        self.keys_pressed.add(event.keysym)
    def key_release(self, event):
        self.keys_pressed.discard(event.keysym)
    def update(self):
        if not self.typing:
            self.player.set_sprinting("x" in self.keys_pressed)
            if "Left" in self.keys_pressed:
                self.player.move_left()
            if "Right" in self.keys_pressed:
                self.player.move_right()
            if "Up" in self.keys_pressed:
                self.player.move_up()
            if "Down" in self.keys_pressed:
                self.player.move_down()
        self.check_room_transitions()
        self.root.after(16, self.update)
    def run(self):
        self.root.mainloop()