import tkinter as tk
from pathlib import Path
from rooms import ROOMS
from PIL import Image, ImageTk
from player import Player
from dialogue_box import DialogueBox
import json
from audiomanager import AudioManager
from menu import Menu
BASE_DIR = Path(__file__).resolve().parent
class Game:
    def __init__(self):
        self.root = tk.Tk()
        icon_path = BASE_DIR / "sprites" / "assets" / "taskbar_logo.png"
        icon = ImageTk.PhotoImage(Image.open(icon_path))
        self.root.iconphoto(True, icon)
        self.icon = icon
        self.setup_window()
        self.viewport_width = 320
        self.viewport_height = 240
        self.scale = 1.0
        self.camera_x = 0
        self.camera_y = 0
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
        self.player_hitbox_debug = None
        self.interaction_debug = None
        self.exit_debug = []
        self.debug_mode = True # Set to True to view player coordinates and collision hitboxes for player and collision
        self.widescreen_mode = False
        self.keys_pressed = set()
        self.direction_keys = []
        # Load assets
        self.audio = AudioManager()
        self.load_room("myroom")
        # Create game objects
        self.player = Player(self)
        self.menu = Menu(self)
        # Draw everything once
        self.render_static()
        self.update_debug_hud()
        self.state = "playing"
        self.update()
        self.typing = True
        with open(BASE_DIR / "eng.json", encoding="utf-8") as f:
            self.dialogue_data = json.load(f)
        self.type_text()
    def load_dialogue(self):
        self.dialogue_index = 0 
        self.dialogue_box = DialogueBox(self)
    def setup_window(self):
        self.root.title("DELTARUNE Chapter 6")
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
        return (self.offset_x + (x - self.camera_x) * self.scale, self.offset_y + (y - self.camera_y) * self.scale)
    def ui_to_screen(self,x,y):
        return(
            self.offset_x + x * self.scale,
            self.offset_y + y * self.scale)
    def update_scale(self):
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < 2 or height < 2:
            return

        self.scale = min(
            width / self.viewport_width,
            height / self.viewport_height)
        draw_width = int(self.viewport_width * self.scale)
        draw_height = int(self.viewport_height * self.scale)
        self.offset_x = (width - draw_width) // 2
        self.offset_y = (height - draw_height) // 2
    def update_camera(self):
        sprite_width = self.player.animation.sprite_width
        sprite_height = self.player.animation.sprite_height
        player_center_x = self.player.x + sprite_width / 2
        player_center_y = self.player.y + sprite_height / 2
        if self.game_width > self.viewport_width:
            target_x = player_center_x - self.viewport_width / 2
            max_x = self.game_width - self.viewport_width
            self.camera_x = max(0, min(target_x, max_x))
        else:
            self.camera_x = 0

        if self.game_height > self.viewport_height:
            target_y = player_center_y - self.viewport_height / 2
            max_y = self.game_height - self.viewport_height
            self.camera_y = max(0, min(target_y, max_y))
        else:
            self.camera_y = 0
    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, width=320, height=240, highlightthickness=0, bd=0, bg = "black")
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
    def load_room(self, room_id):
        room = ROOMS[room_id]
        self.room = room
        background_path = BASE_DIR/"room_backgrounds"/room.background

        # print(f"Loaded room: {room.name}") #Debug for room loading, keep this commented out unless testing room loading.

        self.background_pil = Image.open(background_path)
        self.game_width = self.background_pil.width
        self.game_height = self.background_pil.height
        self.on_resize()
        self.background_image = ImageTk.PhotoImage(self.background_pil)
        if self.background_sprite is None:
            self.background_sprite = self.canvas.create_image(0,0, image = self.background_image, anchor = "nw")
        else: 
            self.canvas.itemconfig(self.background_sprite, image=self.background_image)
        
        for rect in self.collision_debug:
            self.canvas.delete(rect)
        self.collision_debug.clear()
        
        if hasattr(self, "player"):
            self.canvas.tag_raise(self.player.canvas_sprite)
            self.player.room = room
        if room.music:
            self.audio.play_music(room.music)
    def check_room_transitions(self):
        for exit in self.room.exits:
            if self.player.is_touching_exit(exit):
                self.change_room(exit)
                break
    def change_room(self,exit):
        self.load_room(exit.destination)
        self.player.x = exit.spawn_x
        self.player.y = exit.spawn_y
    #     print(
    #     f"Room: {self.room.name}, "
    #     f"Player: ({self.player.x}, {self.player.y}), "
    #     f"Camera: ({self.camera_x}, {self.camera_y}), "
    #     f"Scale: {self.scale}, "
    #     f"Offset: ({self.offset_x}, {self.offset_y})"
    # )
        self.render_static()
    def on_resize(self, event=None):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 2 or canvas_height < 2:
            return
        self.update_scale()
        self.render_static()
    def render_static(self):
        self.render_background()
        self.menu.render_static()
        self.render_debug_static()
        self.dialogue_box.render_static()
    def render_dynamic(self):
        self.render_background_dynamic()
        if hasattr(self, "player"):
            self.player.render()
        if self.menu.visible:
            self.menu.render_dynamic()
            self.canvas.tag_raise("menu")
        self.render_debug_dynamic()
        self.update_debug_hud()
        self.canvas.tag_raise(self.debug_text)
    def rectangles_overlap(a,b):
        left1, top1, right1, bottom1 = a
        left2, top2, right2, bottom2 = b
        return (
            right1 > left2 and
            left1 < right2 and
            bottom1 > top2 and
            top1 < bottom2)
    def render_debug_static(self):
        if not self.debug_mode:
            return
        for rect, left, top, right, bottom in self.collision_debug:
            self.canvas.delete(rect)
        self.collision_debug.clear()
        for left, top, right, bottom in self.room.collisions:
            rect = self.canvas.create_rectangle(
                0, 0, 0, 0,
                outline="red",
                width=2,
                tags="debug")
            self.collision_debug.append(
                (rect, left, top, right, bottom))
        for exit in self.room.exits:
            left = exit.x
            top = exit.y
            right = exit.x + exit.width
            bottom = exit.y + exit.height
            rect = self.canvas.create_rectangle(
                0, 0, 0, 0,
                outline="green",
                width=2,
                tags="debug")
            self.collision_debug.append(
                (rect, left, top, right, bottom))
    def render_debug_dynamic(self):
        if not self.debug_mode:
            return
        for rect, left, top, right, bottom in self.collision_debug:
            left_screen, top_screen = self.game_to_screen(left, top)
            right_screen, bottom_screen = self.game_to_screen(right, bottom)
    #         print(
    #     f"Room coords: ({left}, {top}, {right}, {bottom}) "
    #     f"-> Screen coords: "
    #     f"({left_screen}, {top_screen}, {right_screen}, {bottom_screen})"
    # )
            self.canvas.coords(
                rect,
                left_screen,
                top_screen,
                right_screen,
                bottom_screen)
        left, top, right, bottom = self.player.get_interaction_box()
        left_screen, top_screen = self.game_to_screen(left, top)
        right_screen, bottom_screen = self.game_to_screen(right, bottom)
        if self.interaction_debug is None:
            self.interaction_debug = self.canvas.create_rectangle(
                0, 0, 0, 0,
                outline="yellow",
                width=2,
                tags="debug")
        self.canvas.coords(
            self.interaction_debug,
            left_screen,
            top_screen,
            right_screen,
            bottom_screen)
    def update_debug_hud(self):
        if not self.debug_mode:
            self.canvas.itemconfigure(self.debug_text, state="hidden")
            return
        self.canvas.itemconfigure(self.debug_text, state="normal")
        if (self.player.x, self.player.y) != self.player.x or self.player.y:
            self.canvas.itemconfig(
                self.debug_text,
                text=(
                    f"Room: {self.room.name}\n"
                    f"X: {self.player.x:.1f}\n"
                    f"Y: {self.player.y:.1f}\n"))
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

            x, y = self.game_to_screen(0,0)

            self.canvas.coords(
                self.background_sprite,
                x,
                y)
    def render_background_dynamic(self):
        x, y = self.game_to_screen(0,0)
        self.canvas.coords(self.background_sprite, x, y)
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
    def interact(self, event = None):
        interaction_box = self.player.get_interaction_box()
        # print(interaction_box) #Uncomment only if you want the dimensions of the interaction box to be printed in the terminal window
    def bind_keys(self):
        self.root.bind("<KeyPress>", self.key_press)
        self.root.bind("<KeyRelease>", self.key_release)
        self.root.bind("<space>", self.advance_dialogue)
        self.root.bind("<z>", self.advance_dialogue)
        self.root.bind("<z>", self.interact)
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("<c>", self.toggle_menu)
    def key_press(self, event):
        self.keys_pressed.add(event.keysym)
        if event.keysym in ("Left","Right","Up","Down"):
            if event.keysym in self.direction_keys:
                self.direction_keys.remove(event.keysym)
            self.direction_keys.append(event.keysym)
        if self.state == 'menu':
            if event.keysym == 'Up':
                self.menu.move_up()
            elif event.keysym == 'Down':
                self.menu.move_down()
    def key_release(self, event):
        self.keys_pressed.discard(event.keysym)
        if event.keysym in self.direction_keys:
            self.direction_keys.remove(event.keysym)
    def toggle_menu(self, event = None):
        if self.state == "playing":
            self.menu.open()
            self.state = "menu" 
            self.player.animation.finish_at_rest_frame()
        elif self.state == "menu":
            self.menu.close()
            self.state = "playing"
    def update(self):
        if self.state == "playing":
            moved = bool(self.keys_pressed & {"Left","Right","Up","Down"})
            started_moving = moved and not self.was_moving
            if started_moving:
                self.player.speed = self.player.walk_speed
            if "Left" in self.keys_pressed:
                self.player.move_left()
                moved = True
            if "Right" in self.keys_pressed:
                self.player.move_right()
                moved = True
            if "Up" in self.keys_pressed:
                self.player.move_up()
                moved = True
            if "Down" in self.keys_pressed:
                self.player.move_down()
                moved = True
            if self.direction_keys:
                self.player.facing = self.direction_keys[0].lower()
            if moved:
                if "x" in self.keys_pressed:
                    self.player.speed = min(self.player.speed + self.player.acceleration,self.player.run_speed)
                    self.player.animation.animation_speed = self.player.run_animation_speed
                else:
                    self.player.speed = self.player.walk_speed
                    self.player.animation.animation_speed = self.player.walk_animation_speed
                # print(self.player.speed)
                self.player.animation.play(self.player.facing)
            else:
                self.player.animation.stop()
            self.was_moving = moved
        self.check_room_transitions()
        self.update_camera()
        self.render_dynamic()
        self.player.animation.update()
        self.root.after(32, self.update) # Framerate, lower number = higher framerate
    def run(self):
        self.root.mainloop()