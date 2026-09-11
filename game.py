from fileinput import filename
import tkinter as tk
import time
from pathlib import Path
from animated_sprite import AnimatedSprite
from rooms import ROOMS
from PIL import Image, ImageTk
# from chapterselect import ChapterSelect
from ui_sprites import UISpriteSheet
from hud import HUD
from player import Player
from fileselect import FileMenu
from dialogue_box import DialogueBox
import json
from audiomanager import AudioManager
from menu import Menu
from progress import ProgressTracker
from chapter_intro import ChapterIntro
from legend import LegendSequence
from chapter_logo import ChapterLogoSequence
import os #file manip


BASE_DIR = Path(__file__).resolve().parent
uiSpritesheetPath = BASE_DIR/"sprites"/"ui"/"menu+HUD_spritesheet.png" #unbelievably cursed having it here, but if we need to reuse it for anything else we can easily rename the var  

''' 
    TODO LIST:
        -multiple voices in a dialogue, and faceplate support for dialogue.
        -dialogue choices and branching paths.
        
        Bug Fixin'
        -dialogue text does not scale with the window size, and the dialogue box thickness does not scale with the window size.
        -closing dialogue after it finishes also seems to be bugged, but it might be more related to progressing dialogue
            rather than closing it.
        -some movement animations can still play when dialogue is active.
        -pressing escape needs to close the game, but will we need to add the config menu in the dark world to change fullscreen to compensate - escape should be done now, but needs testing
        -the config menu needs to be added to the dark world.
'''


class Game:
    def __init__(self, startup = None, start_hidden = False):
        # INITALIZATION
        # relating to screen size
        self.startup = startup
        self.start_hidden = start_hidden
        # Startup screens use explicit game states so the same Tk window
        # can move through intro -> legend/logo -> file select.
        self.state = "boot"
        self.root = tk.Tk()
        if self.start_hidden:
            self.root.withdraw()
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
        
        #slot stuff
        #remove later, for now exists to initalize the file select
        self.slot1 = type('Slot', (), {})()  # Create a simple object for slot1
        self.slot1.name = "-----"
        self.slot2 = type('Slot', (), {})()  # Create a simple object for slot1
        self.slot2.name = "-----"
        self.slot3 = type('Slot', (), {})()  # Create a simple object for slot1
        self.slot3.name = "-----"
        
        # screen display
        self.create_widgets()
        self.load_dialogue()

        # print("ui_sprites loaded from:", ui_sprites.__file__)
        # print("UISpriteSheet has get:", hasattr(UISpriteSheet, "get"))
        self.ui_sprites = UISpriteSheet(self)
        self.hud = HUD(self)
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
        
        # controls 
        self.bind_keys()
        self.collision_debug = []
        self.player_hitbox_debug = None
        self.interaction_debug = None
        self.exit_debug = []
        self.pending_room = None
        self.pending_spawn = None
        self.pending_facing = None
        self.was_moving = False
        self.keys_pressed = set()
        self.direction_keys = []
        #obj_time quitting behavior variables
        self.quit_timer = 0.0 #for closing the game by holding it down
        self.escape_held = False
        self.quit_last_update = time.perf_counter()

        # Brief delay so the final frame of the quit animation can play
        self.quit_finishing = False
        self.quit_finish_started = None
        self.quit_final_hold = 0.15
        
        #other init
        self.debug_mode = False # Set to True to view player coordinates and collision hitboxes for player and collision
        self.widescreen_mode = False
        self.transitioning = False
        self.fade_alpha = 0
        self.fade_duration = 250 #milliseconds for half the fade transition
        self.fade_start_time = None
        self.fade_mode = None

        # Fade used specifically for the startup-screen -> File Select handoff.
        self.file_select_fade_active = False
        self.file_select_fade_started_at = None
        self.file_select_fade_duration = 0.75

        self.audio = AudioManager()
        self.progress = ProgressTracker()
        self.active_startup_screen = None
        # ======================================================
        # QUITTING... sprite
        # Equivalent to spr_quitmessage
        # ======================================================

        quit_sheet = Image.open(
            uiSpritesheetPath
        ).convert("RGBA")

        self.quit_frames = []

        QUIT_X = 6
        QUIT_Y = 430
        QUIT_WIDTH = 87
        QUIT_HEIGHT = 10
        QUIT_Y_SPACING = 12

        TRANSPARENT_COLOR = (210, 129, 252)

        for i in range(5):
            top = QUIT_Y + i * QUIT_Y_SPACING

            frame = quit_sheet.crop(
                (
                    QUIT_X,
                    top,
                    QUIT_X + QUIT_WIDTH,
                    top + QUIT_HEIGHT,
                )
            ).convert("RGBA")

            pixels = frame.load()

            for y in range(frame.height):
                for x in range(frame.width):
                    r, g, b, a = pixels[x, y]

                    if (r, g, b) == TRANSPARENT_COLOR:
                        pixels[x, y] = (r, g, b, 0)

            self.quit_frames.append(frame)

        self.quit_photo = None
        
        # file select
        # Keep track of the Canvas items FileMenu creates so Game can hide
        # the file-select screen until the startup sequence has finished.
        file_menu_items_before = set(self.canvas.find_all())
        self.file_menu = FileMenu(self)
        self.file_menu.create_widgets()
        file_menu_items_after = set(self.canvas.find_all())
        self.file_menu_canvas_items = list(
            file_menu_items_after - file_menu_items_before
        )

        # Startup screen controllers. They all draw into this same Canvas;
        # game.py only decides which one owns the screen at a given moment.
        self.chapter_intro = ChapterIntro(
            self,
            on_complete=self.finish_chapter_intro
        )
        self.legend_sequence = LegendSequence(
            self,
            on_complete=self.finish_legend
        )
        self.chapter_logo = ChapterLogoSequence(
            self,
            chapter=6,
            on_complete=self.finish_chapter_logo
        )

        # Inventory
        self.LW_inventory = [
            "Ball of Junk",
            "Glass",
            "BlackShard"
        ]
        
        # Create basic game objects
        self.load_room("mainMenu", play_music=False)
        self.player = Player(self)
        self.menu = Menu(self)
        # self.chapter_select = ChapterSelect(self)
        
        # Draw everything once finished initializing, so that the game starts with a fully rendered screen
        self.render_static()
        self.update_debug_hud()
        self.transitioning = False

        # Do not jump straight to File Select. Chapter 6 now owns its
        # startup flow inside this same Game process.
        self._set_file_menu_visible(False)
        self.startup_started = False
        self.update()
        if not self.start_hidden:
            self.show_window()
        '''self.typing = True
        with open(BASE_DIR / "eng.json", encoding="utf-8") as f:
            self.dialogue_data = json.load(f)
        self.type_text()'''
    # ======================================================
    # CHAPTER 6 STARTUP FLOW
    # ======================================================

    STARTUP_SCREEN_STATES = {
        "chapter_intro",
        "legend",
        "chapter_logo",
    }

    def show_window(self):

        self.root.deiconify()

        self.fullscreen = True
        self.root.attributes(
            "-fullscreen",
            True,
        )

        self.root.update_idletasks()

        self.on_resize()

        if not self.startup_started:
            self.startup_started = True
            self.start_chapter_startup()

        if self.active_startup_screen is not None:
            self.active_startup_screen.render()

        # Force Windows/Tk to actually create and paint the window
        # before chapter6.py signals readiness.
        self.root.update_idletasks()
        self.root.update()

    def launch_chapter(self, chapter):
        if chapter != 6:
            return

        print("Initializing Chapter 6")
        self.start_chapter_startup()

    def _get_startup_route_override(self):
        """
        Optional development/testing override.

        Supported values:
            "chapter_intro"
            "legend"
            "file_select"

        The normal game does not need to provide this. It is useful while
        testing the sequence before real completion files exist.
        """

        if isinstance(self.startup, dict):
            return self.startup.get("startup_route")

        if self.startup is not None:
            return getattr(
                self.startup,
                "startup_route",
                None
            )

        return None

    def determine_chapter_startup_route(self):
        """
        Current Chapter 6 startup rule.

        Chapter 5's recovered initializer routes completed chapter data to:
            room_legend -> PLACE_LOGO -> PLACE_MENU

        Until the Chapter 4-style mid-chapter rules are implemented, both a
        brand-new Chapter 6 and an in-progress Chapter 6 use chapter_intro.
        """

        override = self._get_startup_route_override()

        if override in {
            "chapter_intro",
            "legend",
            "file_select",
        }:
            return override

        if self.progress.completed_chapter_any_slot(6):
            return "legend"

        return "chapter_intro"

    def start_chapter_startup(self):
        route = self.determine_chapter_startup_route()

        if route == "legend":
            self.start_legend()
        elif route == "file_select":
            self.start_file_select()
        else:
            self.start_chapter_intro()

    def _prepare_startup_screen(self):
        """
        Hide normal gameplay UI while one of the startup controllers owns
        the Canvas.
        """

        self._set_file_menu_visible(False)

        try:
            self.menu.close()
        except Exception:
            pass

        try:
            self.hud.close()
        except Exception:
            pass

        try:
            self.dialogue_box.hide()
        except Exception:
            pass

    def _hide_active_startup_screen(self):
        if self.active_startup_screen is None:
            return

        try:
            self.active_startup_screen.hide()
        except Exception:
            pass

        self.active_startup_screen = None

    def start_chapter_intro(self):
        self._hide_active_startup_screen()
        self._prepare_startup_screen()

        self.state = "chapter_intro"
        self.active_startup_screen = self.chapter_intro
        self.chapter_intro.start()

    def finish_chapter_intro(self):
        # ChapterIntro finishes on a completely black frame. File Select is
        # revealed underneath a black Game overlay, then faded into view.
        self.start_file_select(fade_in=True)

    def start_legend(self):
        self._hide_active_startup_screen()
        self._prepare_startup_screen()

        self.state = "legend"
        self.active_startup_screen = self.legend_sequence
        self.legend_sequence.start()

    def finish_legend(self):
        # Direct Python equivalent of obj_legend eventually going to
        # PLACE_LOGO.
        self.start_chapter_logo()

    def start_chapter_logo(self):
        self._hide_active_startup_screen()
        self._prepare_startup_screen()

        self.state = "chapter_logo"
        self.active_startup_screen = self.chapter_logo
        self.chapter_logo.start()

    def finish_chapter_logo(self):
        # Startup PROCESS_LOGO (global.plot == 0) goes to PLACE_MENU.
        self.start_file_select()

    def start_file_select(self, fade_in=False):

        if fade_in:
            self.fade_alpha = 255
            self.file_select_fade_active = True
            self.file_select_fade_started_at = (
                time.perf_counter()
            )
        else:
            self.file_select_fade_active = False
            self.file_select_fade_started_at = None
            self.fade_alpha = 0

        self._hide_active_startup_screen()

        self.state = "file_select"

        open_file_menu = getattr(
            self.file_menu,
            "open",
            None,
        )

        if callable(open_file_menu):
            try:
                open_file_menu()
            except TypeError:
                pass

        self._set_file_menu_visible(True)

        try:
            self.file_menu.render_static()
        except Exception:
            pass

        self._set_file_menu_visible(True)

        if fade_in:
            self.render_fade()

    def _set_file_menu_visible(self, visible):
        """
        FileMenu predates the new startup state machine, so this helper works
        with both styles:
          * FileMenu.show()/hide(), if those exist
          * FileMenu.canvas_items, if that exists
          * the exact Canvas items captured when FileMenu.create_widgets()
            ran in __init__
        """

        state = "normal" if visible else "hidden"

        method_name = "show" if visible else "hide"
        method = getattr(
            self.file_menu,
            method_name,
            None
        )

        if callable(method):
            try:
                method()
            except TypeError:
                pass

        items = set(
            getattr(
                self,
                "file_menu_canvas_items",
                []
            )
        )

        file_menu_owned = getattr(
            self.file_menu,
            "canvas_items",
            None
        )

        if file_menu_owned:
            items.update(file_menu_owned)

        for item in items:
            try:
                self.canvas.itemconfigure(
                    item,
                    state=state
                )
            except tk.TclError:
                pass

        # Harmless fallback for FileMenu revisions that use a common tag.
        for tag in ("file_menu", "filemenu"):
            try:
                self.canvas.itemconfigure(
                    tag,
                    state=state
                )
            except tk.TclError:
                pass

        if visible:
            for item in items:
                try:
                    self.canvas.tag_raise(item)
                except tk.TclError:
                    pass

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
        # self.root.bind("<Escape>",self.quit_game)
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
    #quit the game by holding down the escape key for a few seconds, to prevent accidental quitting
    # def quit_game(self, event = None):
    #     if self.isEscapeHeld:
    #         return
            
    #     self.isEscapeHeld = True
    #     self.escapePressTime = time.time()
    #     # self.quitAnimated.play("quit")
        
    #     # Start checking the hold condition
    #     self.quit_game_hold()
    # def quit_game_hold(self, event = None):
    #     if not self.isEscapeHeld:
    #         return

    #     elapsed = time.time() - self.escapePressTime
        
    #     if elapsed >= self.escapeKeyHoldDuration:
    #         self.end_program()
    #     else:
    #         # Re-check every 100 milliseconds
    #         self.root.after(100, self.quit_game_hold)
        
    # def quit_game_release(self, event = None):
    #     #"isEscapeHeld" removes quitting button   
    #     self.isEscapeHeld = False
    #     self.escapePressTime = None
    #     self.quitAnimated.stop()
    #     if self.quittingSprite is not None:
    #         self.canvas.itemconfigure(
    #             self.quittingSprite,
    #             state="hidden"
    #         )
    def update_quit(self):
        """
        Python equivalent of obj_time's Escape/quit_timer logic,
        with a tiny final-frame hold before closing.
        """

        now = time.perf_counter()

        dt = now - self.quit_last_update
        self.quit_last_update = now

        dt = min(dt, 0.1)

        # --------------------------------------------------
        # Final QUITTING... frame
        # --------------------------------------------------
        if self.quit_finishing:
            self.quit_timer = 30.0

            if (
                now - self.quit_finish_started
                >= self.quit_final_hold
            ):
                self.end_program()
                return False

            return True

        # --------------------------------------------------
        # Normal obj_time behavior
        # --------------------------------------------------
        if self.escape_held:
            if self.quit_timer < 0:
                self.quit_timer = 0

            self.quit_timer += dt * 30.0

            if self.quit_timer >= 30:
                self.quit_timer = 30.0
                self.quit_finishing = True
                self.quit_finish_started = now

        else:
            self.quit_timer -= dt * 60.0

        return True
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
        self.quittingSprite = None
        self.fade_overlay = self.canvas.create_image(
            0,
            0,
            anchor = "nw"
        )
        self.fade_photo = None
    def load_room(self, room_id, facing_direction = None, play_music = True):
        room = ROOMS[room_id]
        self.room = room

        background_ref = Path(room.background)

        if background_ref.is_absolute():
            # An explicitly absolute path.
            background_path = background_ref

        elif len(background_ref.parts) > 1:
            # A project-relative path, for example:
            # "sprites/intro/spr_giantdarkdoor.png"
            background_path = BASE_DIR / background_ref

        else:
            # Existing rooms can continue supplying only a filename.
            background_path = (
                BASE_DIR
                / "room_backgrounds"
                / background_ref
            )

        if not background_path.exists():
            raise FileNotFoundError(
                f"Could not find background for room '{room_id}': "
                f"{background_path}"
            )

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
        if play_music and room.music:
            self.audio.play_music(room.music)
    def check_room_transitions(self):
        for exit in self.room.exits:
            if self.player.is_touching_exit(exit):
                self.change_room(exit)
                break
    def change_room(self, exit):
        if self.transitioning:
            return
        if self.state == "menu":
            self.menu.close()
            self.hud.close()
            self.state = "playing"
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

        if self.state in self.STARTUP_SCREEN_STATES:
            self._set_file_menu_visible(False)
            if self.active_startup_screen is not None:
                self.active_startup_screen.render()

        elif self.state == "file_select":
            self._set_file_menu_visible(True)

        if self.fade_alpha > 0:
            self.render_fade()

    def render_static(self):
        self.render_background()
        self.hud.render_static()
        self.menu.render_static()

        # Capture any FileMenu items that are created lazily by render_static().
        file_menu_items_before = set(self.canvas.find_all())
        self.file_menu.render_static()
        file_menu_items_after = set(self.canvas.find_all())

        self.file_menu_canvas_items = list(
            set(self.file_menu_canvas_items)
            | (file_menu_items_after - file_menu_items_before)
        )

        self.render_debug_static()
        self.dialogue_box.render_static()

        # FileMenu existed before the new startup flow and its render_static()
        # may make items visible. Keep it hidden until PLACE_MENU/file_select.
        if self.state != "file_select":
            self._set_file_menu_visible(False)

        if (
            self.state in self.STARTUP_SCREEN_STATES
            and self.active_startup_screen is not None
        ):
            self.active_startup_screen.render()

    def render_dynamic(self):
        # Startup screens own the full Canvas. Do not render Kris/HUD/menu on
        # top of them.
        if self.state in self.STARTUP_SCREEN_STATES:
            if self.active_startup_screen is not None:
                self.active_startup_screen.render()
            self.render_fade()
            return

        # FileMenu owns the screen once the startup sequence reaches
        # PLACE_MENU.
        if self.state == "file_select":
            self._set_file_menu_visible(True)
            self.render_fade()
            return

        self.render_background_dynamic()

        #special renders, like the player, the menu, dialog, etc
        if hasattr(self, "player"):
            self.player.render()
        # if self.isEscapeHeld: #if holding the button then display it
        #     self.quitAnimated.update()
        #     self.renderQuit()
        if self.menu.visible:
            self.menu.render_dynamic()
            self.canvas.tag_raise("menu")

        if self.dialogue_box.visible:
            self.dialogue_box.layout_widgets()

        self.render_debug_dynamic()
        self.update_debug_hud()
        self.canvas.tag_raise(self.debug_text)
        self.render_fade()

    def renderQuit(self):
        """
        Equivalent to:

        if (quit_timer >= 1)
            draw_sprite_ext(
                spr_quitmessage,
                quit_timer / 7,
                4, 4,
                2, 2,
                0,
                c_white,
                quit_timer / 15
            );
        """

        if self.quit_timer < 1:
            if self.quittingSprite is not None:
                self.canvas.itemconfigure(
                    self.quittingSprite,
                    state="hidden"
                )
            return

        # ---------------------------------------------
        # GameMaker:
        #     image_index = quit_timer / 7
        #
        # Fractional sprite indexes effectively resolve
        # to their corresponding animation frame.
        # ---------------------------------------------
        frame_index = int(self.quit_timer / 7)

        frame_index = max(
            0,
            min(frame_index, len(self.quit_frames) - 1)
        )

        frame = self.quit_frames[frame_index].copy()

        # ---------------------------------------------
        # GameMaker:
        #     image_alpha = quit_timer / 15
        # ---------------------------------------------
        alpha = max(
            0.0,
            min(1.0, self.quit_timer / 15.0)
        )

        if alpha < 1.0:
            alpha_channel = frame.getchannel("A")

            alpha_channel = alpha_channel.point(
                lambda value: round(value * alpha)
            )

            frame.putalpha(alpha_channel)

        # ---------------------------------------------
        # DELTARUNE draws this sprite x2 at 640x480.
        #
        # Our logical framebuffer is 320x240, so the
        # native 87x10 sprite already represents that
        # same apparent size.
        # ---------------------------------------------
        scaled_width = max(
            1,
            round(frame.width * self.scale)
        )

        scaled_height = max(
            1,
            round(frame.height * self.scale)
        )

        scaled = frame.resize(
            (
                scaled_width,
                scaled_height
            ),
            Image.Resampling.NEAREST
        )

        self.quit_photo = ImageTk.PhotoImage(scaled)

        # GameMaker uses (4,4) in a 640x480 GUI.
        # Equivalent position in our 320x240 logical viewport:
        canvas_x, canvas_y = self.ui_to_screen(2, 2)

        if self.quittingSprite is None:
            self.quittingSprite = self.canvas.create_image(
                canvas_x,
                canvas_y,
                image=self.quit_photo,
                anchor="nw",
                tags=("quit_message",)
            )
        else:
            self.canvas.coords(
                self.quittingSprite,
                canvas_x,
                canvas_y
            )

            self.canvas.itemconfigure(
                self.quittingSprite,
                image=self.quit_photo,
                state="normal"
            )

        # obj_time's GUI drawing should remain above the
        # room, menu, dialogue, startup screens, and fades.
        self.canvas.tag_raise(self.quittingSprite)
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
        if self.state != "playing":
            return
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
    def handle_z(self, event = None):
        if self.transitioning:
            return
        if self.state == "menu":
            self.menu.confirm()
            return
        self.advance_dialogue(event)
        self.interact(event)
        # print(interaction_box) #Uncomment only if you want the dimensions of the interaction box to be printed in the terminal window
    def bind_keys(self):
        self.root.bind("<KeyPress>", self.key_press)
        self.root.bind("<KeyRelease>", self.key_release)
        # self.root.bind("<KeyRelease-Escape>", self.quit_game_release)
        self.root.bind("<space>", self.advance_dialogue)
        self.root.bind("<space>", self.interact)
        self.root.bind("<Configure>", self.on_resize)
    def key_press(self, event):
        key = event.keysym

        if key == "Escape":
            self.escape_held = True
            return
        if self.transitioning:
            return

        # Ignore repeated KeyPress events while a key is held.
        if key in self.keys_pressed:
            return
        self.keys_pressed.add(key)

        # --------------------------------------------------
        # Startup screen input
        # --------------------------------------------------
        if self.state in self.STARTUP_SCREEN_STATES:
            if self.active_startup_screen is not None:
                self.active_startup_screen.handle_input(key)
            return

        # --------------------------------------------------
        # File Select input
        # --------------------------------------------------
        if self.state == "file_select":
            if self.file_select_fade_active:
                return

            handle_input = getattr(
                self.file_menu,
                "handle_input",
                None
            )

            if callable(handle_input):
                handle_input(key)

            # Do not allow file-select keys to leak into Kris/menu controls.
            return

        # C = menu open / close
        if key == "c":
            self.toggle_menu()
            return
        elif key == "z":
            self.handle_z()
            return

        # Menu controls
        if self.state == "menu":
            if key == "Up":
                self.menu.move_up()
                return
            elif key == "Down":
                self.menu.move_down()
                return
            elif key == "x":
                self.handle_menu_back()
                return

        # Direction keys
        if key in (
            "Left",
            "Right",
            "Up",
            "Down"):
            if key in self.direction_keys:
                self.direction_keys.remove(key)
            self.direction_keys.append(key)

    def key_release(self, event):
        if event.keysym == "Escape":
            self.escape_held = False
            return
        self.keys_pressed.discard(event.keysym)
        if event.keysym in self.direction_keys:
            self.direction_keys.remove(event.keysym)
    def handle_menu_back(self):
        if self.transitioning:
            return
        if self.state != "menu":
            return
        # Inside a submenu:
        # X returns to the main menu.
        if self.menu.screen != "main":
            self.menu.back()
            return
        # Main menu:
        # X closes the entire menu.
        self.menu.close()
        self.hud.close()
        self.state = "playing"
    def toggle_menu(self, event=None):
        if self.transitioning:
            return
        if self.state == "playing":
            self.menu.open()
            self.hud.open()
            self.state = "menu"
            self.player.animation.stop_at_next_rest_frame()
            return
        if self.menu.screen != "main":
            return
        self.menu.close()
        self.hud.close()
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

                # possibly for special dialogue where the player is still moving, ala the chapter 2 chat scene with noelle about december?
                self.start_dialogue(
                    trigger.dialogue,
                    lock_player=False)

                if trigger.once:
                    self.triggered_events.add(trigger.id)
                return
    '''
        Main Menu functions: 
            -Load(), which continues the game from a saved slot.
            -Erase(), which erases a saved slot.
            -Copy(), which copies a saved slot to another slot.
            -New(), which creates a new saved slot. (with the option to carry over data from a previous save, like the original game)
            -ChangeLanguage(), which changes the language of the game. 
                (with the option to change it back to english, or to a different language)
            -EndProgram(), which ends the program and closes the game.
        
        Other Expectations for the main menu:
            -The room has three save slots split apart in a similar manner as the dialogue boxes weve made
            -dont forget the "CHAPTER 6" text at the top left of the screen, and the "DELTARUNE" text at the bottom right of the screen.
                (in addition to copyright info and stuff)
            -not sure how much we wanna put into language support, but the modes of language should have a unique character set
    '''
    def load(self, slot):
        # Load the game from the specified slot
        # first we find our save file
        filename = f"filech6_{slot}.json"
        
        #then we fetch the data
        with open(filename, "r") as file:
            data = json.load(file)
                
        #then give it a return and handle it in the main menu
        return data

    def save(self, slot, data):
        # where data is a dictionary containing the game state to be saved (e.g. "{plrX: 0, plrY: 0, room: "room_id", flags: {...}}")
        # Save the game to the specified slot
        filename = f"filech6_{slot}.json"
        
        with open(filename, "w") as file:
            json.dump(data, file, indent=4)
        print("Game saved successfully!") #temp for ensuring things work, delete later
        pass
    def erase(self, slot):
        # Erase the specified save slot
        filename = f"filech6_{slot}.json"
        
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Save slot {slot} erased successfully.") #temp for ensuring things work, delete later
        else:
            print(f"Save slot {slot} does not exist.") #temp for ensuring things work, delete later
        pass
    def copy(self, source_slot, target_slot):
        # Copy the game from source_slot to target_slot
        loaded_data = self.load(source_slot)
        self.save(target_slot, loaded_data)
        #pretty neat to reuse save functions, right?
        
        print(f"Save slot {source_slot} copied to {target_slot}.") #temp for ensuring things work, delete later
        pass
    def new(self, slot):
        # Create a new save slot from a possible DltRn chapter 5 save file, or just a blank save file if none is provided
        # TODO
        pass
    def change_language(self, language):
        # Change the language of the game
        # TODO
        pass            
    def end_program(self):
        # End the program and close the game
        self.root.destroy()
        #yeah thats kinda it just call this function to close the game lol
    #Main Update function
    def update(self):
        #obj_time exists outside of individual room/game logic
        if not self.update_quit():
            return
        if self.transitioning:
            self.update_transition()
            self.renderQuit()
            self.root.after(16, self.update)
            return

        # --------------------------------------------------
        # Chapter startup screens
        # --------------------------------------------------
        if self.state in self.STARTUP_SCREEN_STATES:
            screen = self.active_startup_screen

            if screen is not None:
                screen.update()

                # update() may finish the screen and immediately move to the
                # next state, so only render it again if it is still active.
                if self.active_startup_screen is screen:
                    screen.render()

            self.renderQuit()
            frame_ms = (
                getattr(screen, "FRAME_MS", 16)
                if screen is not None
                else 16
            )
            self.root.after(frame_ms, self.update)
            return

        # --------------------------------------------------
        # File Select
        # --------------------------------------------------
        if self.state == "file_select":
            self._set_file_menu_visible(True)

            if self.file_select_fade_active:
                elapsed = time.perf_counter() - self.file_select_fade_started_at
                progress = min(
                    elapsed / self.file_select_fade_duration,
                    1.0
                )
                self.fade_alpha = round(255 * (1.0 - progress))
                self.render_fade()

                if progress >= 1.0:
                    self.file_select_fade_active = False
                    self.file_select_fade_started_at = None
                    self.fade_alpha = 0
                    self.render_fade()

            self.render_dynamic()
            self.renderQuit()

            self.root.after(32, self.update)
            return

        if self.state == "playing":
            movement_keys_held = bool(
                self.keys_pressed & {"Left", "Right", "Up", "Down"}
            )

            started_moving = movement_keys_held and not self.was_moving

            if not self.dialogue_blocks_movement:
                if started_moving:
                    self.player.speed = self.player.walk_speed

                moved = False

                if "Left" in self.keys_pressed:
                    if self.player.move_left():
                        moved = True

                if "Right" in self.keys_pressed:
                    if self.player.move_right():
                        moved = True

                if "Up" in self.keys_pressed:
                    if self.player.move_up():
                        moved = True

                if "Down" in self.keys_pressed:
                    if self.player.move_down():
                        moved = True

                if self.direction_keys:
                    self.player.facing = self.direction_keys[0].lower()

            else:
                moved = False

            # --------------------------------
            # Animation
            # --------------------------------

            if moved:
                if "x" in self.keys_pressed:
                    self.player.speed = min(
                        self.player.speed + self.player.acceleration,
                        self.player.run_speed
                    )
                    self.player.animation.animation_speed = (
                        self.player.run_animation_speed
                    )
                else:
                    self.player.speed = self.player.walk_speed
                    self.player.animation.animation_speed = (
                        self.player.walk_animation_speed
                    )

                self.player.animation.play(self.player.facing)

            else:
                if self.was_moving:
                    if movement_keys_held:
                        # Kris is holding a direction but cannot move.
                        # Finish the current walking cycle.
                        self.player.animation.finish_current_cycle()
                    else:
                        # Kris stopped because the movement key was released.
                        # Naturally advance to the appropriate rest frame.
                        self.player.animation.stop_at_next_rest_frame()

            self.was_moving = moved

            self.check_room_transitions()
            self.update_camera()
            self.hud.update_position()

            if self.dialogue_box.visible:
                self.dialogue_box.update_position()

            self.render_dynamic()
            self.player.animation.update()
            self.check_dialogue_triggers()

        elif self.state == "menu":
            # Keep the camera/UI alive, but do not run room transitions,
            # movement, or dialogue triggers while the menu owns input.
            self.update_camera()
            self.hud.update_position()

            if self.dialogue_box.visible:
                self.dialogue_box.update_position()

            self.render_dynamic()
        self.renderQuit()
        self.root.after(32, self.update) # Framerate, lower number = higher framerate

    def run(self):
        self.root.mainloop()