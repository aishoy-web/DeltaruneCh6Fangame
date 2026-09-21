from fileinput import filename
import tkinter as tk
import time
import subprocess
import sys
import tempfile
from pathlib import Path
from animated_sprite import AnimatedSprite
from rooms import ROOMS
from PIL import Image, ImageTk
from ui_sprites import UISpriteSheet
from hud import HUD
from player import Player
from fileselect import FileMenu
from dialogue_box import DialogueBox
from dialogue import DialogueWriter
import json
from audiomanager import AudioManager
from menu import Menu
from progress import ProgressTracker
from chapter_intro import ChapterIntro
from legend import LegendSequence
from chapter_logo import ChapterLogoSequence
from opening_scene import OpeningScene
import os #file manip
import random
from lw_items import (
    ITEM_ACTIONS,
    get_dw_weapon_id,
    get_lw_item_description,
    get_lw_item_name,
    get_lw_weapon_strength,
    is_lw_weapon,
    normalize_lw_item_id,
)


BASE_DIR = Path(__file__).resolve().parent
uiSpritesheetPath = BASE_DIR/"sprites"/"ui"/"menu+HUD_spritesheet.png" #unbelievably cursed having it here, but if we need to reuse it for anything else we can easily rename the var  
CHAPTER_SELECT_ENTRY = (
    BASE_DIR / "chapterselect.py"
)

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

        # ==================================================
        # LIGHT WORLD STATS
        # ==================================================

        self.lcharname = "Kris"

        self.llv = 1

        self.lhp = 20
        self.lmaxhp = 20

        self.lat = 10
        self.lwstrength = 0

        self.ldf = 10
        self.ladef = 0

        self.lweapon = 0
        self.larmor = 3

        self.lgold = 2
        self.lxp = 0

        # Equivalent to global.flag[914].
        self.kris_preservation_society = 0
        
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
        # DialogueWriter is now the authoritative typewriter.
        # These legacy fields remain synchronized for compatibility
        # with older room/cutscene code that may still inspect them.
        self.character_index = 0
        self.typewriter_timer = 0
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

        self.chapter_select_process = None
        self.chapter_select_ready_file = None
        self.chapter_select_handoff_launched = False

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
        self.file_menu = FileMenu(
            self,
            on_file_selected=self.handle_file_selection,
            on_chapter_select=(
                self.return_to_chapter_select
            ),
        )
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
        # Light World inventory now uses the original numeric
        # global.litem IDs.  This lets USE/INFO/DROP and weapon
        # swapping match the GML behavior.
        self.LW_inventory = [
            5,   # Ball of Junk
            11,  # Glass
            17,  # BlackShard
        ]

        # Numeric Light World flags used by item-specific behavior.
        self.light_world_flags = {}

        # ITEM / INFO / DROP dialogue now uses the same DialogueWriter
        # as room and trigger dialogue.  No separate Tk after() typewriter
        # state is needed here.
        
        # Create basic game objects
        self.load_room("mainMenu", play_music=False)
        self.player = Player(self)
        self.menu = Menu(self)
        self.opening_scene = OpeningScene(self)
        self.current_save_slot = None
        self.current_save_data = None
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

    def return_to_chapter_select(self):
        """
        Freeze File Select, stop its music, and begin
        loading Chapter Select immediately.

        File Select remains visible until Chapter Select
        signals that its first complete frame is ready.
        """

        if self.state == "chapter_select_handoff":
            return

        self.state = "chapter_select_handoff"

        self.chapter_select_handoff_launched = False

        # Freeze the exact visible File Select frame and
        # stop its music immediately.
        try:
            self.file_menu.freeze_for_handoff()
        except Exception:
            pass

        # No fade. Start loading Chapter Select now.
        self._launch_chapter_select_handoff()

    def _launch_chapter_select_handoff(self):
        """
        Launch Chapter Select only after Chapter 6 has
        completely faded to black.
        """

        if self.chapter_select_handoff_launched:
            return

        self.chapter_select_handoff_launched = True

        # ----------------------------------------------
        # Create unique ready-file path.
        # ----------------------------------------------

        fd, ready_path = tempfile.mkstemp(
            prefix="deltarune_chapter_select_ready_",
            suffix=".tmp",
        )

        os.close(fd)

        # We only wanted tempfile to generate a unique path.
        try:
            os.remove(
                ready_path
            )
        except OSError:
            pass

        self.chapter_select_ready_file = (
            ready_path
        )

        # ----------------------------------------------
        # Launch Chapter Select.
        #
        # --select:
        #     bypass startup completion/continue prompt
        #
        # --ready-file:
        #     Chapter Select signals when its first frame
        #     has actually been prepared.
        # ----------------------------------------------

        try:
            self.chapter_select_process = (
                subprocess.Popen(
                    [
                        sys.executable,
                        str(
                            CHAPTER_SELECT_ENTRY
                        ),
                        "--select",
                        "--ready-file",
                        ready_path,
                    ],
                    cwd=str(BASE_DIR),
                )
            )

        except Exception as exc:
            print(
                "[Game] Could not launch "
                "Chapter Select:",
                exc,
            )

            self._cancel_chapter_select_handoff()

    def _cancel_chapter_select_handoff(self):
        """
        Restore File Select if Chapter Select could not
        start successfully.
        """

        if self.chapter_select_ready_file:
            try:
                os.remove(
                    self.chapter_select_ready_file
                )
            except OSError:
                pass

        self.chapter_select_ready_file = None
        self.chapter_select_process = None
        self.chapter_select_handoff_launched = False
        self.chapter_select_handoff_started_at = None

        self.fade_alpha = 0
        self.render_fade()

        self.state = "file_select"

        try:
            self.file_menu.start()
        except Exception:
            pass

    def update_chapter_select_handoff(self):
        """
        Keep the frozen File Select visible until
        Chapter Select signals that it is ready.
        """

        ready_path = (
            self.chapter_select_ready_file
        )

        if ready_path is None:
            return

        # ----------------------------------------------
        # Chapter Select is ready.
        # ----------------------------------------------

        if os.path.exists(
            ready_path
        ):
            try:
                os.remove(
                    ready_path
                )
            except OSError:
                pass

            self.chapter_select_ready_file = None

            # The new fullscreen Chapter Select is already
            # visible. Remove the old Chapter 6 window now.
            try:
                self.root.destroy()
            except tk.TclError:
                pass

            return

        # ----------------------------------------------
        # Failure protection
        # ----------------------------------------------

        if (
            self.chapter_select_process is not None
            and self.chapter_select_process.poll()
            is not None
        ):
            print(
                "[Game] Chapter Select exited before "
                "signaling readiness. Exit code:",
                self.chapter_select_process.returncode,
            )

            self._cancel_chapter_select_handoff()

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
            if self.dialogue_writer.active:
                self.dialogue_writer.stop(
                    hide_box=True
                )
            else:
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

    def start_opening_scene(
        self,
        slot=None,
        save_data=None,
        is_new_file=False,
    ):
        """Leave File Select and begin the Chapter 6 playable prologue."""
        if self.state == "opening_scene":
            return

        self.file_select_fade_active = False
        self.file_select_fade_started_at = None
        self._set_file_menu_visible(False)
        self.current_save_slot = slot
        self.current_save_data = save_data
        self.kris_preservation_society = int(
            (save_data or {}).get(
                "kris_preservation_society",
                0,
            )
        )
        save_data = save_data or {}

        self.lweapon = int(
            save_data.get(
                "lweapon",
                0,
            )
        )

        self.larmor = int(
            save_data.get(
                "larmor",
                0,
            )
        )

        self.lxp = int(
            save_data.get(
                "lxp",
                0,
            )
        )

        self.llv = int(
            save_data.get(
                "llv",
                1,
            )
        )

        self.lgold = int(
            save_data.get(
                "lgold",
                2,
            )
        )

        self.lhp = int(
            save_data.get(
                "lhp",
                20,
            )
        )

        self.lmaxhp = int(
            save_data.get(
                "lmaxhp",
                20,
            )
        )

        self.lat = int(
            save_data.get(
                "lat",
                10,
            )
        )

        self.ldf = int(
            save_data.get(
                "ldf",
                10,
            )
        )

        self.lwstrength = int(
            save_data.get(
                "lwstrength",
                0,
            )
        )

        self.ladef = int(
            save_data.get(
                "ladef",
                0,
            )
        )
        imported_inventory = save_data.get(
            "LW_inventory"
        )

        if imported_inventory is not None:
            self.LW_inventory = [
                item_id
                for item_id in (
                    normalize_lw_item_id(item)
                    for item in imported_inventory
                )
                if item_id not in (None, 0)
            ][:8]
        print(
            "[Opening Scene] lweapon =",
            self.lweapon,
        )
        self.opening_scene.start(
            save_slot=slot,
            save_data=save_data,
            is_new_file=is_new_file,
        )
        print(
            "[Save Import] flag[914] =",
            self.kris_preservation_society,
        )

    def handle_file_selection(
        self,
        kind,
        slot,
        source_path=None,
    ):
        """Own the File Select -> Chapter 6 state transition.

        FileSelect only reports the confirmed selection. This method loads or
        initializes the selected data, then chooses OpeningScene as the next
        game state.
        """
        if kind == "continue":
            try:
                data = self.load(
                    slot,
                    start_game=False,
                )
            except (FileNotFoundError, json.JSONDecodeError):
                # FileSelect also recognizes official/INI-backed Chapter 6
                # data. The opening currently needs only the selected slot, so
                # preserve the handoff even before that loader is implemented.
                data = {
                    "slot": slot,
                    "chapter": 6,
                    "source": "existing_file",
                }
            is_new_file = False

        elif kind == "new":
            data = self.new(
                slot,
                start_game=False,
            )
            is_new_file = True

        elif kind == "import_previous":

            light_stats = (
                self.read_deltarune_pc_light_stats(
                    source_path
                )
            )

            light_inventory = (
                self.read_deltarune_pc_light_inventory(
                    source_path
                )
            )

            self.kris_preservation_society = (
                self.read_deltarune_pc_flag(
                    source_path,
                    914,
                    default=0,
                )
            )

            print(
                "[Save Import] flag[914] =",
                self.kris_preservation_society,
            )

            print(
                "[Save Import] Light World stats =",
                light_stats,
            )

            data = {
                "slot": slot,
                "chapter": 6,
                "source_chapter": 5,

                "previous_file": (
                    str(source_path)
                    if source_path is not None
                    else None
                ),

                "kris_preservation_society":
                    self.kris_preservation_society,

                # Light World state imported from Chapter 5.
                **light_stats,
                "LW_inventory": light_inventory,

                "opening_complete": False,
            }

            is_new_file = True

        else:
            raise ValueError(
                f"Unknown File Select handoff: {kind!r}"
            )

        self.start_opening_scene(
            slot=slot,
            save_data=data,
            is_new_file=is_new_file,
        )

    def read_deltarune_pc_light_stats(
        self,
        save_path,
    ):
        """
        Read DELTARUNE's Light World STAT values from a
        Windows/PC save file.

        Offsets correspond to the serialization order used
        by scr_load().
        """

        defaults = {
            "lweapon": 0,
            "larmor": 0,
            "lxp": 0,
            "llv": 1,
            "lgold": 2,
            "lhp": 20,
            "lmaxhp": 20,
            "lat": 10,
            "ldf": 10,
            "lwstrength": 0,
            "ladef": 0,
        }

        if save_path is None:
            return defaults.copy()

        try:
            save_path = Path(save_path)

            lines = save_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()

            offsets = {
                "lweapon": 525,
                "larmor": 526,
                "lxp": 527,
                "llv": 528,
                "lgold": 529,
                "lhp": 530,
                "lmaxhp": 531,
                "lat": 532,
                "ldf": 533,
                "lwstrength": 534,
                "ladef": 535,
            }

            result = defaults.copy()

            for key, line_index in offsets.items():

                if 0 <= line_index < len(lines):

                    raw_value = lines[
                        line_index
                    ].strip()

                    result[key] = int(
                        float(raw_value)
                    )

            return result

        except (
            OSError,
            ValueError,
            TypeError,
        ):
            return defaults.copy()

    def read_deltarune_pc_light_inventory(
        self,
        save_path,
    ):
        """
        Read the eight global.litem[] slots from a Windows/PC
        DELTARUNE save.

        After ladef (line 535), PC saves interleave:
            litem[0], phone[0], litem[1], phone[1], ...
        The eight litem lines are therefore 536, 538, ... 550.
        """

        if save_path is None:
            return []

        try:
            save_path = Path(save_path)

            lines = save_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()

            inventory = []

            for slot in range(8):
                line_index = 536 + slot * 2

                if not (0 <= line_index < len(lines)):
                    break

                item_id = int(
                    float(
                        lines[line_index].strip()
                    )
                )

                # global.litem uses 0 for an empty slot.
                if item_id != 0:
                    inventory.append(item_id)

            return inventory

        except (
            OSError,
            ValueError,
            TypeError,
        ):
            return []

    def read_deltarune_pc_flag(
        self,
        save_path,
        flag_index,
        default=0,
    ):
        """
        Read one global.flag[] value from a PC DELTARUNE save.

        This follows the non-console serialization order used
        by scr_load().
        """

        if save_path is None:
            return default

        try:
            save_path = Path(save_path)

            lines = save_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()

            # PC save structure:
            #
            # 552 serialized values appear before flag[0].
            flag_block_start = 552

            line_index = (
                flag_block_start
                + int(flag_index)
            )

            if not (
                0 <= line_index < len(lines)
            ):
                return default

            raw_value = lines[
                line_index
            ].strip()

            return int(float(raw_value))

        except (
            OSError,
            ValueError,
            TypeError,
        ):
            return default

    # ======================================================
    # LIGHT WORLD ITEM SYSTEM
    # ======================================================

    def _play_optional_item_sfx(self, filename):
        """
        Play a Light World item sound when the asset exists.
        Supports both sfx/ and audio/sfx/ project layouts.
        """

        for directory in (
            BASE_DIR / "sfx",
            BASE_DIR / "audio" / "sfx",
        ):
            path = directory / filename

            if path.exists():
                try:
                    import pygame
                    pygame.mixer.Sound(
                        str(path)
                    ).play()
                except Exception:
                    pass
                return

    def _refresh_light_world_ui(self):
        try:
            self.hud.update_text()
        except Exception:
            pass

        try:
            self.menu.render_static()
            self.menu.render_dynamic()
        except Exception:
            pass

    def _finish_item_dialogue(
        self,
        on_complete=None,
    ):
        """
        Return control to the overworld after an ITEM/INFO/DROP writer
        finishes.  The menu and its HUD remain closed, matching the
        original menuno == 9 handoff.
        """

        self.state = "playing"
        self._sync_dialogue_compat_state()

        if callable(on_complete):
            on_complete()

    def start_item_dialogue(
        self,
        messages,
        on_complete=None,
    ):
        """
        Route ITEM / INFO / DROP text through the same DialogueWriter
        used by ordinary room dialogue.
        """

        clean_messages = [
            str(message)
            for message in messages
            if str(message)
        ]

        self.menu.close()
        self.hud.close()

        if not clean_messages:
            self.state = "playing"

            if callable(on_complete):
                on_complete()

            return

        # Item actions do not use room.dialogue and therefore do not set
        # dialogue_active/dialogue_blocks_movement. The explicit state owns
        # the input/movement lock instead.
        self.state = "item_dialogue"
        self.dialogue_active = False
        self.dialogue_blocks_movement = False
        self.choice_active = False

        self.dialogue_box.clear_portrait()

        self.dialogue_writer.start(
            clean_messages,
            typer=1,
            on_complete=lambda: self._finish_item_dialogue(
                on_complete
            ),
            auto_close=True,
            show_box=True,
        )

        self._sync_dialogue_compat_state()
        self.canvas.tag_raise("dialogue")

    def advance_item_dialogue(self):
        """
        Z/Space behavior is now owned by DialogueWriter:
            typing -> reveal the current page
            finished -> advance
            final page -> close
        """

        if self.state != "item_dialogue":
            return

        if not self.dialogue_writer.active:
            self._finish_item_dialogue()
            return

        self.dialogue_writer.advance_or_skip()
        self._sync_dialogue_compat_state()

    def activate_light_world_item_action(
        self,
        inventory_index,
        action_index,
    ):
        """
        Execute USE / INFO / DROP for the selected litem slot.
        """

        if not (
            0 <= inventory_index
            < len(self.LW_inventory)
        ):
            return

        try:
            action = ITEM_ACTIONS[
                int(action_index)
            ]
        except (IndexError, TypeError, ValueError):
            return

        item_id = normalize_lw_item_id(
            self.LW_inventory[
                inventory_index
            ]
        )

        if item_id is None:
            return

        if action == "USE":
            messages = self.use_light_world_item(
                inventory_index,
                item_id,
            )

        elif action == "INFO":
            messages = self.get_light_world_item_info(
                item_id
            )

        else:
            messages = self.drop_light_world_item(
                inventory_index,
                item_id,
            )

        self._refresh_light_world_ui()
        self.start_item_dialogue(messages)

    def get_light_world_item_info(self, item_id):
        messages = get_lw_item_description(
            item_id
        )

        # scr_litemdesc gives Ball of Junk one extra page
        # when Dark World item 1 is present.  Support that
        # automatically if a later system exposes a DW set.
        if item_id == 5:
            dark_items = set(
                getattr(
                    self,
                    "dark_world_item_ids",
                    [],
                )
            )

            if 1 in dark_items:
                messages = [
                    '* "Ball of Junk" - A small ball of accumulated things in your pocket.',
                    "* It smells like scratch'n'sniff marshmallow stickers.",
                ]

        return messages

    def can_equip_light_world_weapon(
        self,
        item_id,
    ):
        """
        Original rule: Kris may equip the Light World weapon
        only when the paired Dark World weapon is owned or
        equipped.

        The current fangame has no complete DW equipment
        model yet, so absence of DW tracking means "allow".
        Once one of these sets exists, the original rule is
        enforced automatically.
        """

        dw_id = get_dw_weapon_id(
            item_id
        )

        if dw_id is None:
            return False

        inventory = getattr(
            self,
            "dark_world_weapon_ids",
            None,
        )

        equipped = getattr(
            self,
            "dark_world_equipped_weapon_ids",
            None,
        )

        if inventory is None and equipped is None:
            return True

        inventory = set(inventory or [])
        equipped = set(equipped or [])

        return (
            dw_id in inventory
            or dw_id in equipped
        )

    def equip_light_world_weapon(
        self,
        inventory_index,
        new_weapon_id,
    ):
        """
        Python equivalent of scr_lweaponeq.

        The selected inventory slot receives the previously
        equipped Light World weapon, and the selected weapon
        becomes equipped.
        """

        old_weapon_id = int(
            getattr(
                self,
                "lweapon",
                0,
            )
        )

        if (
            0 <= inventory_index
            < len(self.LW_inventory)
        ):
            if old_weapon_id == 0:
                # global.litem would receive 0.  This project
                # represents occupied slots as a compact list,
                # so removing the entry is equivalent.
                del self.LW_inventory[
                    inventory_index
                ]
            else:
                self.LW_inventory[
                    inventory_index
                ] = old_weapon_id

        self.lweapon = int(
            new_weapon_id
        )

        self.lwstrength = (
            get_lw_weapon_strength(
                self.lweapon
            )
        )

    def recover_light_world_hp(
        self,
        amount,
    ):
        """
        Exact scr_lrecover semantics.

        Note: reaching max HP sets maxed_out=True, even when
        HP was actually recovered on that use.
        """

        amount = int(amount)
        recovered = amount
        maxed_out = False

        if self.lhp < self.lmaxhp:
            self.lhp += amount
        else:
            maxed_out = True

        if (
            self.lhp >= self.lmaxhp
            and not maxed_out
        ):
            self.lhp = self.lmaxhp
            maxed_out = True

        return recovered, maxed_out

    def _consume_lw_inventory_slot(
        self,
        inventory_index,
    ):
        if (
            0 <= inventory_index
            < len(self.LW_inventory)
        ):
            del self.LW_inventory[
                inventory_index
            ]

    def use_light_world_item(
        self,
        inventory_index,
        item_id,
    ):
        """
        Common scr_litemuseb behavior.

        Chapter-5-only NPC/room branches are intentionally
        left as future context hooks; their ordinary fallback
        behavior is implemented here.
        """

        item_id = int(item_id)

        # ------------------------------
        # Weapons
        # ------------------------------
        if is_lw_weapon(item_id):

            if not self.can_equip_light_world_weapon(
                item_id
            ):
                return [
                    "* For some reason you couldn't equip it."
                ]

            name = get_lw_item_name(
                item_id
            )

            self.equip_light_world_weapon(
                inventory_index,
                item_id,
            )

            self._play_optional_item_sfx(
                "snd_item.wav"
            )

            return [
                f"* You equipped the {name}."
            ]

        # ------------------------------
        # Other Light World items
        # ------------------------------
        if item_id == 1:
            self._play_optional_item_sfx(
                "snd_swallow.wav"
            )

            self._consume_lw_inventory_slot(
                inventory_index
            )

            return [
                "* You drank the hot chocolate.\n"
                "* It tasted wonderful.\n"
                "* Your throat tightened..."
            ]

        if item_id == 3:
            recovered, maxed_out = (
                self.recover_light_world_hp(
                    1
                )
            )

            self._consume_lw_inventory_slot(
                inventory_index
            )

            if maxed_out:
                recovery_text = (
                    "* Your HP was maxed out."
                )
            else:
                recovery_text = (
                    f"* You recovered {recovered} HP!"
                )

            return [
                "* You re-applied the bandage.\n"
                + recovery_text
            ]

        if item_id == 4:
            return [
                "* You held out the flowers.\n"
                "* A floral scent fills the air.\n"
                "* Nothing happened."
            ]

        if item_id == 5:
            return [
                "* You looked at the junk ball in admiration.\n"
                "* Nothing happened."
            ]

        if item_id == 8:
            self._play_optional_item_sfx(
                "snd_egg.wav"
            )
            return [
                "* You used the Egg."
            ]

        if item_id == 9:
            return [
                "* You held the cards.\n"
                "* They felt flimsy between your fingers."
            ]

        if item_id == 10:
            # This is the default Kris-alone branch from
            # scr_litemuseb.  NPC/party-specific Chapter 5
            # branches can override this later.
            self._consume_lw_inventory_slot(
                inventory_index
            )

            self.lhp = 19
            self.light_world_flags[
                342
            ] = 1

            return [
                "* (You unhesitatingly devoured the box of heart shaped candies.)",
                "* (Your guts are being destroyed.)",
                "* (You accept this destruction as part of life...)",
            ]

        if item_id == 11:
            return [
                "* It doesn't seem very useful."
            ]

        # There is no case 14 in scr_litemuseb.
        # Selecting USE on Wristwatch therefore creates no
        # item dialogue and simply exits the menu action.
        if item_id == 14:
            return []

        if item_id == 19:
            return [
                "* (You held it up in the air.)"
            ]

        if item_id == 20:
            return [
                "* (Bread.)"
            ]

        if item_id == 21:
            return [
                "* (You cannot use it right now.)"
            ]

        if item_id == 0:
            return [
                "* You grasped at nothing."
            ]

        return []

    def drop_light_world_item(
        self,
        inventory_index,
        item_id,
    ):
        """
        obj_overworldc DROP behavior for the normal
        Light World state.
        """

        item_id = int(item_id)
        name = get_lw_item_name(
            item_id
        )

        # ------------------------------
        # Protected items
        # ------------------------------
        if item_id == 5:
            # The original delegates this one to scr_text(10);
            # that script was not among the recovered sources.
            return [
                "* You couldn't throw the Ball of Junk away."
            ]

        if item_id == 9:
            return [
                "* (You fumbled and caught them. You can't throw these away!)"
            ]

        if item_id == 11:
            return [
                "* (For some reason you felt like if you throw it away...)",
                "* (It would be like throwing away someone's... ???)",
                "* (... but you didn't fully understand it.)",
            ]

        if item_id == 21:
            return [
                "* (The seeds stick to everything and cannot be thrown away.)"
            ]

        if is_lw_weapon(
            item_id
        ):
            return [
                "* (Recently, seems like weapons can't be thrown away so easily.)"
            ]

        # ------------------------------
        # Successful drop
        # ------------------------------
        if item_id == 8:
            message = "* What Egg?"

            if (
                self.light_world_flags.get(
                    263,
                    0,
                )
                == 0
            ):
                self.light_world_flags[
                    263
                ] = 1

        else:
            roll = random.randint(
                0,
                30,
            )

            if roll == 0:
                message = (
                    f"* You bid a quiet farewell to the {name}."
                )
            elif roll == 1:
                message = (
                    f"* You put the {name} on the ground "
                    "and gave it a little pat."
                )
            elif roll == 2:
                message = (
                    f"* You threw the {name} on the ground "
                    "like the piece of trash it is."
                )
            elif roll == 3:
                message = (
                    f"* You abandoned the {name}."
                )
            else:
                message = (
                    f"* The {name} was thrown away."
                )

        if item_id == 19:
            self.light_world_flags[
                1710
            ] = 1

        self._consume_lw_inventory_slot(
            inventory_index
        )

        return [
            message
        ]

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

    def load_dialogue(self):
        """
        Load localization data and create the unified dialogue stack.

        DialogueWriter corresponds to obj_writer.
        DialogueBox owns the obj_writer_stay-style box/rendering layer.
        """

        self.dialogue_index = 0
        self.dialogue_data = {}

        dialogue_path = BASE_DIR / "eng.json"

        if dialogue_path.exists():
            try:
                with open(
                    dialogue_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    self.dialogue_data = json.load(file)
            except (
                OSError,
                json.JSONDecodeError,
            ):
                self.dialogue_data = {}

        self.dialogue_box = DialogueBox(self)
        self.dialogue_writer = DialogueWriter(
            self,
            self.dialogue_box,
        )

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

        self.background_pil = Image.open(background_path).convert("RGBA")

        # OpeningScene owns temporary night/day variants without requiring a
        # duplicate Room definition. Once real daytime art exists, its single
        # DAY_ROOM_BACKGROUND setting replaces the placeholder treatment.
        if hasattr(self, "opening_scene"):
            self.background_pil = self.opening_scene.apply_room_variant(
                room_id,
                self.background_pil,
            )
        self.game_width = self.background_pil.width
        self.game_height = self.background_pil.height
        self.update_scale()
        self.background_image = ImageTk.PhotoImage(self.background_pil)
        if self.background_sprite is None:
            self.background_sprite = self.canvas.create_image(0,0, image = self.background_image, anchor = "nw")
        else: 
            self.canvas.itemconfig(self.background_sprite, image=self.background_image)
        if hasattr(self, "player"):
            if self.player.canvas_sprite is not None:
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

        elif self.state == "opening_scene":
            self._set_file_menu_visible(False)
            self.opening_scene.render()

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

        if self.state == "opening_scene":
            self.opening_scene.render()

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

        if self.state == "opening_scene":
            self.opening_scene.render()
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
        # Cutscene lerps intentionally produce fractional values, but Pillow's
        # RGBA channels require integers.  Convert only at render time so the
        # underlying fade remains smooth and reusable by the cutscene system.
        render_alpha = max(0, min(255, int(round(self.fade_alpha))))
        if render_alpha <= 0:
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
            (0, 0, 0, render_alpha)
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
    # ======================================================
    # UNIFIED DIALOGUE
    # ======================================================

    def _sync_dialogue_compat_state(self):
        """
        Keep the old Game fields readable while DialogueWriter is the
        authoritative state machine.
        """

        writer = self.dialogue_writer

        self.typing = bool(
            writer.active
            and writer.typing
        )

        self.typing_job = None

        self.dialogue_index = (
            writer.message_index
            if writer.active
            else 0
        )

        self.character_index = sum(
            1
            for glyph in writer.visible_glyphs
            if glyph.char not in (None, "\n")
        )

    def _finish_room_dialogue(self):
        self.dialogue_active = False
        self.dialogue_blocks_movement = False
        self.current_dialogue = None
        self.choice_active = False
        self._sync_dialogue_compat_state()

    def _dialogue_choice_handler(self):
        """
        Return a choice callback only after the project has a concrete
        show_choices() implementation.  Until then, DialogueWriter does not
        freeze a page merely because old Dialogue data contains choices.
        """

        handler = getattr(
            self,
            "show_choices",
            None,
        )

        if not callable(handler):
            return None

        def present(choices):
            self.choice_active = True
            handler(choices)

        return present

    def start_dialogue(
        self,
        dialogue=None,
        lock_player=True,
    ):
        """
        Start room, trigger, or cutscene dialogue through DialogueWriter.

        ``dialogue`` may be:
            None                -> use room.dialogue
            Dialogue            -> one entry
            list[Dialogue]      -> multiple entries
            str / list[str]     -> direct writer text
        """

        if dialogue is None:
            dialogue = getattr(
                self.room,
                "dialogue",
                [],
            )

        if not dialogue:
            return

        # Replace any prior writer cleanly instead of allowing two sets of
        # dialogue state to coexist.
        if self.dialogue_writer.active:
            self.dialogue_writer.stop(
                hide_box=False
            )

        self.dialogue_active = True
        self.dialogue_blocks_movement = bool(
            lock_player
        )
        self.current_dialogue = dialogue
        self.choice_active = False

        self.dialogue_box.clear_portrait()

        self.dialogue_writer.start(
            dialogue,
            text_lookup=self.dialogue_data,
            on_complete=self._finish_room_dialogue,
            on_choices=self._dialogue_choice_handler(),
            auto_close=True,
            show_box=True,
        )

        self._sync_dialogue_compat_state()

    def advance_dialogue(self, event=None):
        if self.state == "item_dialogue":
            self.advance_item_dialogue()
            return

        if self.state != "playing":
            return

        if self.choice_active:
            return

        if not self.dialogue_writer.active:
            return

        self.dialogue_writer.advance_or_skip()
        self._sync_dialogue_compat_state()

    def skip_dialogue(self, event=None):
        """
        X/button2-style writer skip.  This is separate from confirm so
        DELTARUNE's skippable flag can be respected.
        """

        if self.state not in (
            "playing",
            "item_dialogue",
        ):
            return

        if not self.dialogue_writer.active:
            return

        self.dialogue_writer.skip()
        self._sync_dialogue_compat_state()

    def interact(self, event=None):
        if self.state != "playing":
            return

        if self.dialogue_writer.active:
            self.advance_dialogue(event)
            return

        if self.choice_active:
            return

        interaction_box = (
            self.player.get_interaction_box()
        )

        for obj in self.room.interactable_objects:
            obj_box = (
                obj.x,
                obj.y,
                obj.x + obj.width,
                obj.y + obj.height,
            )

            if not self.rectangles_overlap(
                interaction_box,
                obj_box,
            ):
                continue

            if obj.action == "dialogue":
                self.start_dialogue()

            elif obj.action == "scene":
                self.load_scene(
                    obj.data
                )

            elif obj.action == "sound":
                self.audio.play_sound(
                    obj.data
                )

            break

    def handle_z(self, event=None):
        if self.transitioning:
            return

        if self.state == "item_dialogue":
            self.advance_item_dialogue()
            return

        if self.state == "menu":
            self.menu.confirm()
            return

        if self.state != "playing":
            return

        if (
            self.dialogue_writer.active
            or self.dialogue_active
            or self.choice_active
        ):
            self.advance_dialogue(event)
            return

        self.interact(event)
    def bind_keys(self):
        self.root.bind("<KeyPress>", self.key_press)
        self.root.bind("<KeyRelease>", self.key_release)
        # self.root.bind("<KeyRelease-Escape>", self.quit_game_release)
        self.root.bind("<space>", self.handle_z)
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

        # --------------------------------------------------
        # Playable opening (SOUL only)
        # --------------------------------------------------
        if self.state == "opening_scene":
            # Direction state is already recorded in keys_pressed above. The
            # opening controller reads held keys once per logical frame.
            return

        # Dialogue button2 / X skips the remainder of a skippable page.
        if (
            key == "x"
            and self.state in ("playing", "item_dialogue")
            and self.dialogue_writer.active
        ):
            self.skip_dialogue()
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
            elif key == "Left":
                self.menu.move_left()
                return
            elif key == "Right":
                self.menu.move_right()
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
        """
        Backward-compatible alias for older code that still calls
        Game.advance() instead of advance_dialogue().
        """

        if not self.dialogue_writer.active:
            return

        self.dialogue_writer.advance_or_skip()
        self._sync_dialogue_compat_state()
    def check_dialogue_triggers(self):
        if self.dialogue_writer.active:
            return

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
    def load(self, slot, start_game=True):
        """Load a slot and, when selected by File Menu, start the opening."""
        filename = f"filech6_{slot}.json"

        with open(filename, "r") as file:
            data = json.load(file)

        if start_game:
            self.start_opening_scene(
                slot=slot,
                save_data=data,
                is_new_file=False,
            )

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
        # Reading for a copy must not launch the selected slot.
        loaded_data = self.load(source_slot, start_game=False)
        self.save(target_slot, loaded_data)
        #pretty neat to reuse save functions, right?
        
        print(f"Save slot {source_slot} copied to {target_slot}.") #temp for ensuring things work, delete later
        pass
    def new(self, slot, start_game=True):
        # Previous-chapter carry-over data can be added here later. Both new
        # and completed-source files intentionally share the same prologue.
        data = {
            "slot": slot,
            "chapter": 6,
            "room": "myroom",
            "opening_complete": False,
        }
        if start_game:
            self.start_opening_scene(
                slot=slot,
                save_data=data,
                is_new_file=True,
            )
        return data
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
        # Chapter Select handoff
        # --------------------------------------------------

        if self.state == "chapter_select_handoff":

            self.update_chapter_select_handoff()

            self.root.after(
                16,
                self.update
            )

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

        # --------------------------------------------------
        # Chapter 6 playable opening
        # --------------------------------------------------
        if self.state == "opening_scene":
            self.opening_scene.update()
            self.renderQuit()
            self.root.after(self.opening_scene.FRAME_MS, self.update)
            return

        if self.state == "playing":
            if self.dialogue_writer.active:
                self.dialogue_writer.update(1.0)
                self._sync_dialogue_compat_state()

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

        elif self.state == "item_dialogue":
            if self.dialogue_writer.active:
                self.dialogue_writer.update(1.0)
                self._sync_dialogue_compat_state()

            # Item dialogue owns input.  Keep the room/player visible,
            # but freeze movement, room transitions, and menu navigation.
            self.update_camera()
            self.render_background_dynamic()

            if hasattr(self, "player"):
                self.player.render()

            if self.dialogue_box.visible:
                self.dialogue_box.update_position()
                self.dialogue_box.layout_widgets()
                self.canvas.tag_raise("dialogue")

            self.render_debug_dynamic()
            self.update_debug_hud()
            self.canvas.tag_raise(self.debug_text)
            self.render_fade()

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
