import tkinter as tk
import time
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
        self.root.minsize(640, 480) # add minimum size to prvent weird stuff with scaling
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
        self.typewriter_timer = 0
        self.dialogue_active = False
        self.dialogue_active = False
        self.dialogue_blocks_movement = False
        self.current_dialogue = None
        self.triggered_events = set()
        self.story_flags = set()
        self.typing = False
        self.typing_job = None
        self.choice_active = False
        self.collision_debug = []
        self.player_hitbox_debug = None
        self.interaction_debug = None
        self.exit_debug = []
        self.debug_mode = False # Set to True to view player coordinates and collision hitboxes for player and collision
        self.widescreen_mode = False
        self.transitioning = False
        self.fade_alpha = 0
        self.fade_duration = 250 #milliseconds for half the fade transition
        self.fade_start_time = None
        self.fade_mode = None
        self.pending_room = None
        self.pending_spawn = None
        self.pending_facing = None
        self.was_moving = False
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
    def start_dialogue(self, dialogue=None, lock_player=True):
        self.dialogue_active = True
        self.dialogue_blocks_movement = lock_player
        self.dialogue_index = 0
        self.character_index = 0
        self.typing = True
        self.dialogue_box.show()
        self.type_text()
    def load_dialogue(self):
        self.dialogue_index = 0 
        self.dialogue_box = DialogueBox(self)
    def interact(self, event = None):
        if self.dialogue_active:
            self.dialogue_box.advance()
            return
        interaction_rect = self.player.get_interaction_box()
        for obj in self.room.interactable_objects:
            if interaction_rect.colliderect(obj.hitbox):
                obj.interact(self)
                return
    def setup_window(self):
        self.root.title("DELTARUNE Chapter 6")
        self.root.geometry("320x240")
        self.root.configure(bg="black")
        
        # defaults to full screen, but you can toggle it with a keybind below
        self.fullscreen = True
        self.root.attributes("-fullscreen", True)
        
        self.root.bind("<F11>",self.toggle_fullscreen)
        self.root.bind("<Escape>",self.exit_fullscreen)
        self.root.bind("<Configure>", self.window_resized)
    # f11 toggles the fullscreen
    def toggle_fullscreen(self, event = None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        self.root.after(50,self.on_resize)
    # escape only leaves fullscreen.
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
        self.fade_overlay = self.canvas.create_image(
            0,
            0,
            anchor = "nw"
        )
        self.fade_photo = None
    def load_room(self, room_id, facing_direction = None):
        room = ROOMS[room_id]   
        self.room = room
        background_path = BASE_DIR/"room_backgrounds"/room.background

        # print(f"Loaded room: {room.name}") #Debug for room loading, keep this commented out unless testing room loading.

        self.background_pil = Image.open(background_path)
        self.game_width = self.background_pil.width
        self.game_height = self.background_pil.height
        self.update_scale()
        self.background_image = ImageTk.PhotoImage(self.background_pil)
        if self.background_sprite is None:
            self.background_sprite = self.canvas.create_image(0,0, image = self.background_image, anchor = "nw")
        else: 
            self.canvas.itemconfig(self.background_sprite, image=self.background_image)
        if hasattr(self, "player"):
            self.canvas.tag_raise(self.player.canvas_sprite)
            self.player.room = room
            if facing_direction is not None:
                self.player.facing = facing_direction
                self.player.animation.play(facing_direction)
                self.player.animation.stop()
        if room.music:
            self.audio.play_music(room.music)
    def check_room_transitions(self):
        for exit in self.room.exits:
            if self.player.is_touching_exit(exit):
                self.change_room(exit)
                break
    def change_room(self, exit):
        if self.transitioning:
            return
        self.transitioning = True
        self.fade_mode = "out"
        self.fade_alpha = 0
        self.fade_start_time = time.perf_counter()
        self.pending_room = exit.destination
        self.pending_spawn = (exit.spawn_x, exit.spawn_y)
        self.pending_facing = exit.facing_direction
    def on_resize(self, event=None):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width < 2 or canvas_height < 2:
            return
        self.update_scale()
        self.render_static()
        if self.fade_alpha > 0:
            self.render_fade()
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
        if self.dialogue_box.visible:
            self.dialogue_box.update_position()
            self.dialogue_box.layout_widgets()
        self.render_debug_dynamic()
        self.update_debug_hud()
        self.canvas.tag_raise(self.debug_text)
        self.render_fade()
    def render_fade(self):
        if self.fade_alpha <= 0:
            self.canvas.itemconfigure(
                self.fade_overlay,
                state="hidden"
            )
            return
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 2 or height < 2:
            return
        fade_image = Image.new(
            "RGBA",
            (width, height),
            (0, 0, 0, self.fade_alpha)
        )
        self.fade_photo = ImageTk.PhotoImage(fade_image)
        self.canvas.itemconfigure(
            self.fade_overlay,
            image=self.fade_photo,
            state="normal"
        )
        self.canvas.coords(
            self.fade_overlay,
            0,
            0
        )
        self.canvas.tag_raise(self.fade_overlay)
    def rectangles_overlap(self, a, b):
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
    #have the dialogue box type out the text character by character, with a sound effect for each character
    def type_text(self):
        #call the room's dialogue list and get the current dialogue object
        current = self.room.dialogue[self.dialogue_index]
        voice = current.voice
        text = self.dialogue_data.get(current.text_id,current.text_id)
        current_choices = current.choices
        scene_id = current.scene_id
        sound_effect = current.sound_effect
        
        if self.character_index == 0 and sound_effect:
            sound_effect.play()
        #while there is still text left to type, add one character to the dialogue box and play the sound effect
        if self.character_index < len(text):
            self.dialogue_box.set_text(text[:self.character_index+1])
            if voice:
                voice.play()
            
            #advance index and recurse
            self.character_index +=1
            self.typing_job = self.root.after(50, self.type_text)
        else:
            self.typing = False
            self.typing_job = None
            if current_choices: #if the current dialogue has a choice, display them
                self.show_choices(current_choices)
    def advance_dialogue(self, event):
        if self.choice_active:
            return
        current = self.room.dialogue[self.dialogue_index]
        text = current.text_id
        
        #if the player presses the advance key while text is still being typed, finish typing it instantly
        if self.typing:
            self.dialogue_box.set_text(text)
            self.character_index = len(text)
            self.typing = False
            if self.typing_job is not None:
                self.root.after_cancel(self.typing_job)
                self.typing_job = None
            if current.choices: #If the current dialogue has a choice, display them
                self.show_choices(current.choices)
            return
        
        #if its finished, then advance to the next dialogue
        self.dialogue_index += 1
        if self.dialogue_index < len(self.room.dialogue):
            self.dialogue_box.set_text("")
            self.character_index = 0
            self.typing = True
            self.type_text()
        else: # no more dialogue is left, so close the dialogue box
            self.dialogue_box.hide()
            self.typing = False
            self.character_index = 0
            self.dialogue_index = 0
    def start_dialogue(self):
        self.dialogue_box.show()
        self.dialogue_index = 0
        self.character_index = 0
        self.typing = True
        self.type_text()
    def interact(self, event = None):
        # print("Interaction key pressed") #debug for interaction key
        #assuming they are not in a dialogue, choice, or menu, check if they are touching an interactable object
        if self.state != "playing" or self.typing or self.choice_active:
            return
        interaction_box = self.player.get_interaction_box()
        
        #check if any of the interactable objects in the room overlap with the interaction box
        for obj in self.room.interactable_objects:
            obj_box = (obj.x, obj.y, obj.x + obj.width, obj.y + obj.height)
            if self.rectangles_overlap(interaction_box, obj_box):
                if obj.action == "dialogue": #objects like the bed
                    self.start_dialogue()
                elif obj.action == "scene": #doors
                    self.load_scene(obj.data)
                elif obj.action == "sound": #noisemakers
                    self.audio.play_sound(obj.data)
                break
        
        # print(interaction_box) #Uncomment only if you want the dimensions of the interaction box to be printed in the terminal window
    def bind_keys(self):
        self.root.bind("<KeyPress>", self.key_press)
        self.root.bind("<KeyRelease>", self.key_release)
        self.root.bind("<space>", self.advance_dialogue)
        self.root.bind("<space>", self.interact)
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
    def update_transition(self):
        elapsed = (time.perf_counter() - self.fade_start_time) * 1000
        progress = min(elapsed / self.fade_duration, 1.0)
        if self.fade_mode == "out":
            self.fade_alpha = int(progress * 255)
            if progress >= 1.0:
                self.fade_alpha = 255
                self.load_room(
                    self.pending_room,
                    self.pending_facing)
                self.player.x, self.player.y = self.pending_spawn
                self.update_camera()
                self.render_static()
                self.fade_mode = "in"
                self.fade_start_time = time.perf_counter()
        elif self.fade_mode == "in":
            self.fade_alpha = int(255 * (1.0 - progress))
            if progress >= 1.0:
                self.fade_alpha = 0
                self.fade_mode = None
                self.transitioning = False
        self.render_dynamic()
    def advance(self):
        if self.character_index < len(self.current_text):
            # Finish typing
            self.character_index = len(self.current_text)
            return
        if self.dialogue_index < len(self.dialogue) - 1:
             # Next line
             self.dialogue_index += 1
             self.start_line(self.dialogue[self.dialogue_index])
             return
        # Dialogue finished
        self.close_dialogue()
    def check_dialogue_triggers(self):
        player_box = self.player.get_hitbox()
        for trigger in self.room.triggers:
            if trigger.once and trigger.id in self.triggered_events:
                continue

            if trigger.flag is not None:
                if trigger.flag not in self.story_flags:
                    continue

            trigger_box = (
                trigger.x,
                trigger.y,
                trigger.x + trigger.width,
                trigger.y + trigger.height)
            if self.rectangles_overlap(player_box, trigger_box):

                self.start_dialogue(
                    trigger.dialogue,
                    lock_player=False)

                if trigger.once:
                    self.triggered_events.add(trigger.id)
                return
    def update(self):
        if self.transitioning:
            self.update_transition()
            self.root.after(16, self.update)
            return
        if self.state == "playing":
            moved = bool(self.keys_pressed & {"Left","Right","Up","Down"})
            started_moving = moved and not self.was_moving
            if not self.dialogue_blocks_movement:
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
                    moved = True
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
        self.check_dialogue_triggers()
        self.root.after(32, self.update) # Framerate, lower number = higher framerate
    def run(self):
        self.root.mainloop()