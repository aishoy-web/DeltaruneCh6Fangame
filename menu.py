import pygame
from pathlib import Path
from PIL import Image, ImageTk
from lw_items import (
    ITEM_ACTION_CURSOR_POSITIONS,
    LW_ARMOR_NAMES,
    LW_WEAPON_NAMES,
    get_lw_item_name,
)


BASE_DIR = Path(__file__).resolve().parent

cursor_path = (
    BASE_DIR
    / "sprites"
    / "player"
    / "player_red_soul"
    / "spr_heartsmall.png"
)

WEAPON_NAMES = {
    2: "Pencil",
    6: "Halloween Pencil",
    7: "Lucky Pencil",
    12: "Eraser",
    13: "Mech. Pencil",
    15: "Holiday Pencil",
    16: "CactusNeedle",
    17: "BlackShard",
    18: "QuillPen",
    22: "Pencil2",
    23: "Petal",
}

ARMOR_NAMES = {
    3: "Bandage",
    14: "Wristwatch",
}

EXP_THRESHOLDS = {
    1: 10,
    2: 30,
    3: 70,
    4: 120,
    5: 200,
    6: 300,
    7: 500,
    8: 800,
    9: 1200,
    10: 1700,
    11: 2500,
    12: 3500,
    13: 5000,
    14: 7000,
    15: 10000,
    16: 15000,
    17: 25000,
    18: 50000,
    19: 99999,
}

class Menu:
    def __init__(self, game):
        self.game = game

        self.menu_move = pygame.mixer.Sound(
            BASE_DIR /
            "sfx" /
            "snd_menumove.wav"
        )

        self.menu_select = pygame.mixer.Sound(
            BASE_DIR /
            "sfx" /
            "snd_menuselect.wav"
        )

        # ==================================================
        # Canvas items
        # ==================================================

        self.canvas_items = []
        self.option_text = []

        self.menu_sprite = None
        self.menu_sprite_item = None
        self.menu_sprite_stat = None
        self.menu_sprite_cell = None
        self.cursor = None

        self.item_text = []
        self.action_text = []

        self.cell_text = []
        self.cell_font_images = {}

        self.stat_text = {}
        self.stat_font_images = {}

        self.main_font_images = {}
        self.action_font_images = {}

        # ==================================================
        # Menu state
        # ==================================================

        self.visible = False

        # "main" = ITEM / STAT / CELL
        # "item" = inventory screen
        # "stat" = stat screen
        self.screen = "main"

        self.selected = 0
        self.item_selected = 0
        self.item_action_selected = 0
        self.cell_selected = 0

        self.options = [
            "ITEM",
            "STAT",
            "CELL"
        ]

        # Maximum number of inventory entries currently
        # displayed in the Item window.
        self.max_visible_items = 8

        # Recovered menuno == 3 Draw event renders seven
        # global.phonename[] entries.
        self.max_visible_cell_entries = 7

        # ==================================================
        # Main menu position
        # ==================================================

        self.menu_x = 16
        self.menu_y = 84

        # ==================================================
        # Item menu position
        # ==================================================

        # These coordinates are based on the 320x240
        # reference layout.
        self.item_menu_x = 94
        self.item_menu_y = 26

        # ==================================================
        # Stat menu position
        # ==================================================
        self.stat_menu_x = 94
        self.stat_menu_y = 26

        # ==================================================
        # CELL menu position
        # ==================================================
        self.cell_menu_x = 94
        self.cell_menu_y = 26
        self.cell_menu_width = 173
        self.cell_menu_height = 135

        self.stat_positions = {
        "name": (108, 42),

        "lv": (108, 72),
        "hp": (108, 88),

        "at": (108, 120),
        "df": (108, 136),

        "weapon": (108, 166),
        "armor": (108, 182),
        "money": (108, 202),

        # Right-hand column.
        "special_1": (192, 42),
        "special_2": (192, 58),

        "exp": (192, 120),
        "next": (192, 136),
        }

        # ==================================================
        # Soul cursor
        # ==================================================

        self.soul_scale = 1

        self.cursor_image = Image.open(
            cursor_path
        ).convert("RGBA")

        self.cursor_photo = None

        self.refresh_cursor()

    # ======================================================
    # INVENTORY
    # ======================================================

    def get_inventory(self):
        """
        Return the game's current inventory.

        Inventory entries can currently be simple strings,
        such as:

            "Ball of Junk"

        Dictionaries with a "name" field are also supported
        so the inventory system can be expanded later.
        """

        inventory = getattr(
            self.game,
            "LW_inventory",
            []
        )

        return list(inventory)

    def get_item_name(self, item):
        """
        Convert an inventory entry into the canonical
        Light World item name.

        Numeric item IDs are now preferred, but legacy
        string/dict entries remain supported while older
        save/test data is being migrated.
        """

        return get_lw_item_name(item)

    def has_items(self):
        return len(self.get_inventory()) > 0

    # ======================================================
    # CELL / PHONE
    # ======================================================

    def get_phone_entries(self):
        getter = getattr(
            self.game,
            "get_light_world_phone_entries",
            None,
        )

        if callable(getter):
            return list(getter())

        return []

    # ======================================================
    # OVERWORLD STATS
    # ======================================================

    def get_stat_data(self):
        """
        Return the Light World stats displayed by the
        overworld STAT menu.

        Names intentionally correspond to DELTARUNE's
        global.l* variables.
        """

        return {
            "name": getattr(
                self.game,
                "lcharname",
                "Kris"
            ),

            "lv": getattr(
                self.game,
                "llv",
                1
            ),

            "hp": getattr(
                self.game,
                "lhp",
                20
            ),

            "max_hp": getattr(
                self.game,
                "lmaxhp",
                20
            ),

            "at": getattr(
                self.game,
                "lat",
                10
            ),

            "weapon_strength": getattr(
                self.game,
                "lwstrength",
                0
            ),

            "df": getattr(
                self.game,
                "ldf",
                2
            ),

            "armor_defense": getattr(
                self.game,
                "ladef",
                0
            ),

            "weapon": getattr(
                self.game,
                "lweapon",
                0
            ),

            "armor": getattr(
                self.game,
                "larmor",
                0
            ),

            "gold": getattr(
                self.game,
                "lgold",
                2
            ),

            "xp": getattr(
                self.game,
                "lxp",
                0
            ),

            # Corresponds to global.flag[914].
            "kris_preservation_society": getattr(
                self.game,
                "kris_preservation_society",
                0
            ),
        }

    # ======================================================
    # OPTION STATE
    # ======================================================

    def option_enabled(self, index):
        """
        Determine whether a main-menu option can be selected.
        """

        if self.options[index] == "ITEM":
            return self.has_items()

        return True

    def normalize_selection(self):
        """
        Make sure the main-menu cursor is positioned on an
        enabled option.
        """

        if self.option_enabled(self.selected):
            return

        for index in range(len(self.options)):
            if self.option_enabled(index):
                self.selected = index
                return

        self.selected = 0

    # ======================================================
    # CURSOR
    # ======================================================

    def refresh_cursor(self):
        """
        Scale the soul cursor according to the current
        game scale.
        """

        scale = float(self.game.scale)

        cursor_width = max(
            1,
            round(
                self.cursor_image.width
                * scale
                * self.soul_scale
            )
        )

        cursor_height = max(
            1,
            round(
                self.cursor_image.height
                * scale
                * self.soul_scale
            )
        )

        cursor_scaled = self.cursor_image.resize(
            (
                cursor_width,
                cursor_height
            ),
            Image.Resampling.NEAREST
        )

        self.cursor_photo = ImageTk.PhotoImage(
            cursor_scaled
        )

        if self.cursor is not None:
            self.game.canvas.itemconfigure(
                self.cursor,
                image=self.cursor_photo
            )

    # ======================================================
    # WIDGET CREATION
    # ======================================================

    def create_widgets(self):

        # --------------------------------------------------
        # Main menu box
        # --------------------------------------------------

        self.menu_sprite = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.game.ui_sprites.get("menu_box"),
            state="hidden",
            tags=("menu",)
        )

        # --------------------------------------------------
        # Item menu box
        # --------------------------------------------------

        self.menu_sprite_item = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.game.ui_sprites.get(
                "menu_box_item"
            ),
            state="hidden",
            tags=("menu",)
        )

        # --------------------------------------------------
        # Stat menu box
        # --------------------------------------------------

        self.menu_sprite_stat = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.game.ui_sprites.get(
                "menu_box_stat"
            ),
            state="hidden",
            tags=("menu",)
        )

        # --------------------------------------------------
        # CELL menu box
        # --------------------------------------------------

        self.menu_sprite_cell = (
            self.game.canvas.create_rectangle(
                0, 0, 0, 0,
                fill="white",
                outline="",
                state="hidden",
                tags=("menu", "menu_cell"),
            )
        )

        self.menu_cell_inner = (
            self.game.canvas.create_rectangle(
                0, 0, 0, 0,
                fill="black",
                outline="",
                state="hidden",
                tags=("menu", "menu_cell"),
            )
        )

        for _ in range(
            self.max_visible_cell_entries
        ):
            text = self.game.canvas.create_image(
                0,
                0,
                anchor="nw",
                state="hidden",
                tags=("menu", "menu_cell"),
            )
            self.cell_text.append(text)

        # --------------------------------------------------
        # Stat menu text
        # --------------------------------------------------

        for key in self.stat_positions:

            text = self.game.canvas.create_image(
                0,
                0,
                anchor="nw",
                state="hidden",
                tags=("menu",)
            )

            self.stat_text[key] = text

        # --------------------------------------------------
        # Soul cursor
        # --------------------------------------------------

        self.cursor = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.cursor_photo,
            state="hidden",
            tags=("menu",)
        )

        # --------------------------------------------------
        # Main menu options
        # --------------------------------------------------

        for option in self.options:

            image = self.game.ui_sprites.main_font.render(
                option
            )

            text = self.game.canvas.create_image(
                0,
                0,
                anchor="nw",
                image=image,
                state="hidden",
                tags=("menu",)
            )

            self.option_text.append(text)

        # --------------------------------------------------
        # Inventory item text
        # --------------------------------------------------

        for _ in range(self.max_visible_items):

            text = self.game.canvas.create_image(
                0,
                0,
                anchor="nw",
                state="hidden",
                tags=("menu",)
            )

            self.item_text.append(text)

        # --------------------------------------------------
        # Item actions
        # --------------------------------------------------

        for action in (
            "USE",
            "INFO",
            "DROP"
        ):

            text = self.game.canvas.create_image(
                0,
                0,
                anchor="nw",
                state="hidden",
                tags=("menu",)
            )

            self.action_text.append(text)

        self.canvas_items.extend(
            [
                self.menu_sprite,
                self.menu_sprite_item,
                self.menu_sprite_stat,
                self.menu_sprite_cell,
                self.menu_cell_inner,
                self.cursor,
                *self.option_text,
                *self.item_text,
                *self.action_text,
                *self.cell_text,
                *self.stat_text.values(),
            ]
        )

    # ======================================================
    # LAYOUT
    # ======================================================

    def layout_widgets(self):

        # --------------------------------------------------
        # Main menu box
        # --------------------------------------------------

        x, y = self.game.ui_to_screen(
            self.menu_x,
            self.menu_y
        )

        self.game.canvas.coords(
            self.menu_sprite,
            x,
            y
        )

        # --------------------------------------------------
        # Main menu options
        # --------------------------------------------------

        for i, text in enumerate(
            self.option_text
        ):

            x, y = self.game.ui_to_screen(
                42,
                94 + i * 18
            )

            self.game.canvas.coords(
                text,
                x,
                y
            )

        # --------------------------------------------------
        # Item menu box
        # --------------------------------------------------

        x, y = self.game.ui_to_screen(
            self.item_menu_x,
            self.item_menu_y
        )

        self.game.canvas.coords(
            self.menu_sprite_item,
            x,
            y
        )

        # --------------------------------------------------
        # Stat menu box
        # --------------------------------------------------
        x, y = self.game.ui_to_screen(
            self.stat_menu_x,
            self.stat_menu_y)
        self.game.canvas.coords(
            self.menu_sprite_stat,
            x,
            y
        )

        # --------------------------------------------------
        # CELL menu box / entries
        # --------------------------------------------------

        x1, y1 = self.game.ui_to_screen(
            self.cell_menu_x,
            self.cell_menu_y,
        )
        x2, y2 = self.game.ui_to_screen(
            self.cell_menu_x + self.cell_menu_width,
            self.cell_menu_y + self.cell_menu_height,
        )

        self.game.canvas.coords(
            self.menu_sprite_cell,
            x1, y1, x2, y2,
        )

        ix1, iy1 = self.game.ui_to_screen(
            self.cell_menu_x + 3,
            self.cell_menu_y + 3,
        )
        ix2, iy2 = self.game.ui_to_screen(
            self.cell_menu_x + self.cell_menu_width - 3,
            self.cell_menu_y + self.cell_menu_height - 3,
        )

        self.game.canvas.coords(
            self.menu_cell_inner,
            ix1, iy1, ix2, iy2,
        )

        for i, text in enumerate(
            self.cell_text
        ):
            x, y = self.game.ui_to_screen(
                116,
                40 + i * 16,
            )
            self.game.canvas.coords(
                text,
                x,
                y,
            )

        # --------------------------------------------------
        # Stat menu text
        # --------------------------------------------------

        for key, text in self.stat_text.items():

            native_x, native_y = self.stat_positions[key]

            x, y = self.game.ui_to_screen(
                native_x,
                native_y
            )

            self.game.canvas.coords(
                text,
                x,
                y
            )

        # --------------------------------------------------
        # Inventory items
        # --------------------------------------------------

        inventory = self.get_inventory()

        for i, text in enumerate(
            self.item_text
        ):

            if i < len(inventory):

                x, y = self.game.ui_to_screen(
                    116,
                    40 + i * 16
                )

                self.game.canvas.coords(
                    text,
                    x,
                    y
                )

        # --------------------------------------------------
        # Bottom actions
        # --------------------------------------------------

        action_positions = [
            (116, 180),
            (164, 180),
            (221, 180)
        ]

        for text, (native_x, native_y) in zip(
            self.action_text,
            action_positions
        ):

            x, y = self.game.ui_to_screen(
                native_x,
                native_y
            )

            self.game.canvas.coords(
                text,
                x,
                y
            )

    # ======================================================
    # VISIBILITY
    # ======================================================

    def update_visibility(self):

        if not self.visible:
            for item in self.canvas_items:
                self.game.canvas.itemconfigure(
                    item,
                    state="hidden"
                )
            return

        # --------------------------------------------------
        # Main menu
        # --------------------------------------------------

        main_visible = True

        self.game.canvas.itemconfigure(
            self.menu_sprite,
            state="normal")

        for text in self.option_text:
            self.game.canvas.itemconfigure(
                text,
                state="normal")

        # --------------------------------------------------
        # Item menu
        # --------------------------------------------------

        item_visible = (
            self.screen in ("item", "item_action")
        )

        self.game.canvas.itemconfigure(
            self.menu_sprite_item,
            state=(
                "normal"
                if item_visible
                else "hidden"
            )
        )

        for text in self.item_text:
            self.game.canvas.itemconfigure(
                text,
                state=(
                    "normal"
                    if item_visible
                    else "hidden"
            )
        )

        for text in self.action_text:
            self.game.canvas.itemconfigure(
                text,
                state=(
                    "normal"
                    if item_visible
                    else "hidden"
                )
            )

        self.game.canvas.itemconfigure(
            self.cursor,
            state=(
                "normal"
                if self.screen in ("main", "item", "item_action", "cell")
                else "hidden"
            )
        )

        stat_visible = (
            self.screen == "stat"
        )
        self.game.canvas.itemconfigure(
            self.menu_sprite_stat,
            state = (
                "normal"
                if stat_visible
                else "hidden"
            )
        )

        for text in self.stat_text.values():
            self.game.canvas.itemconfigure(
                text,
                state=(
                    "normal"
                    if stat_visible
                    else "hidden"
                )
            )

        cell_visible = (
            self.screen == "cell"
        )

        for item in (
            self.menu_sprite_cell,
            self.menu_cell_inner,
            *self.cell_text,
        ):
            self.game.canvas.itemconfigure(
                item,
                state=(
                    "normal"
                    if cell_visible
                    else "hidden"
                )
            )

    # ======================================================
    # OPEN / CLOSE
    # ======================================================

    def open(self):

        self.visible = True
        self.screen = "main"
        self.selected = 0
        self.item_selected = 0
        self.cell_selected = 0

        self.normalize_selection()

        self.menu_move.play()

        self.render_static()
        self.render_dynamic()
        self.update_visibility()

        self.game.canvas.tag_raise(
            "menu"
        )

    def close(self):

        self.visible = False
        self.screen = "main"

        self.update_visibility()

    # ======================================================
    # MAIN MENU SELECTION
    # ======================================================

    def move_up(self):

        if not self.visible:
            return

        if self.screen == "item":
            self.move_item_up()
            return

        if self.screen == "cell":
            self.move_cell_up()
            return

        if self.screen in ("item_action", "stat"):
            return

        # Already at the top.
        if self.selected == 0:
            return

        start = self.selected

        for index in range(
            self.selected - 1,
            -1,
            -1
        ):

            if self.option_enabled(index):

                self.selected = index
                self.menu_move.play()
                self.render_dynamic()
                return

        self.selected = start

    def move_down(self):

        if not self.visible:
            return

        if self.screen == "item":
            self.move_item_down()
            return

        if self.screen == "cell":
            self.move_cell_down()
            return

        if self.screen in ("item_action", "stat"):
            return

        # Already at the bottom.
        if self.selected == len(self.options) - 1:
            return

        start = self.selected

        for index in range(
            self.selected + 1,
            len(self.options)
        ):

            if self.option_enabled(index):

                self.selected = index
                self.menu_move.play()
                self.render_dynamic()
                return

        self.selected = start

    # ======================================================
    # ITEM MENU SELECTION
    # ======================================================

    def move_item_up(self):

        inventory = self.get_inventory()

        if not inventory:
            return

        if self.item_selected > 0:

            self.item_selected -= 1
            self.menu_move.play()
            self.render_dynamic()

    def move_item_down(self):

        inventory = self.get_inventory()

        if not inventory:
            return

        if (
            self.item_selected
            < min(
                len(inventory),
                self.max_visible_items
            ) - 1
        ):

            self.item_selected += 1
            self.menu_move.play()
            self.render_dynamic()

    def move_cell_up(self):
        entries = self.get_phone_entries()

        if entries and self.cell_selected > 0:
            self.cell_selected -= 1
            self.menu_move.play()
            self.render_dynamic()

    def move_cell_down(self):
        entries = self.get_phone_entries()

        if (
            entries
            and self.cell_selected
            < min(
                len(entries),
                self.max_visible_cell_entries,
            ) - 1
        ):
            self.cell_selected += 1
            self.menu_move.play()
            self.render_dynamic()

    def move_left(self):
        """Move left across USE / INFO / DROP."""

        if not self.visible:
            return

        if self.screen != "item_action":
            return

        if self.item_action_selected <= 0:
            return

        self.item_action_selected -= 1
        self.menu_move.play()
        self.render_dynamic()

    def move_right(self):
        """Move right across USE / INFO / DROP."""

        if not self.visible:
            return

        if self.screen != "item_action":
            return

        if self.item_action_selected >= 2:
            return

        self.item_action_selected += 1
        self.menu_move.play()
        self.render_dynamic()

    # ======================================================
    # CONFIRM / BACK
    # ======================================================

    def confirm(self):

        if not self.visible:
            return

        # --------------------------------------------------
        # Main menu
        # --------------------------------------------------

        if self.screen == "main":

            option = self.options[
                self.selected
            ]

            if option == "ITEM":

                if not self.has_items():
                    return

                self.menu_select.play()

                self.screen = "item"
                self.item_selected = 0

                self.render_static()
                self.render_dynamic()
                self.update_visibility()

                self.game.canvas.tag_raise(
                    "menu"
                )

                return
            elif option == "STAT":
                self.menu_select.play()
                self.screen = "stat"
                self.render_static()
                self.render_dynamic()
                self.update_visibility()
                self.game.canvas.tag_raise("menu")
                return

            elif option == "CELL":
                self.menu_select.play()
                self.screen = "cell"
                self.cell_selected = 0
                self.render_static()
                self.render_dynamic()
                self.update_visibility()
                self.game.canvas.tag_raise("menu")
                return

            return

        # --------------------------------------------------
        # CELL menu
        # --------------------------------------------------

        if self.screen == "cell":
            entries = self.get_phone_entries()

            if not entries:
                return

            self.menu_select.play()

            activate = getattr(
                self.game,
                "activate_light_world_phone",
                None,
            )

            if callable(activate):
                activate(
                    self.cell_selected
                )

            return

        # --------------------------------------------------
        # Item menu
        # --------------------------------------------------

        if self.screen == "item":

            inventory = self.get_inventory()

            if inventory:
                self.menu_select.play()
                self.screen = "item_action"
                self.item_action_selected = 0
                self.render_dynamic()
                self.update_visibility()
                self.game.canvas.tag_raise("menu")

            return

        # --------------------------------------------------
        # USE / INFO / DROP row
        # --------------------------------------------------

        if self.screen == "item_action":

            inventory = self.get_inventory()

            if not inventory:
                self.screen = "main"
                self.normalize_selection()
                self.render_static()
                self.render_dynamic()
                self.update_visibility()
                return

            self.game.activate_light_world_item_action(
                self.item_selected,
                self.item_action_selected,
            )
            return

    def back(self):

        if not self.visible:
            return

        if self.screen == "item_action":
            self.screen = "item"
            self.render_static()
            self.render_dynamic()
            self.update_visibility()
            self.game.canvas.tag_raise("menu")
            return

        if self.screen in ("item", "stat", "cell"):

            if self.screen in ("stat", "cell"):
                self.menu_move.play()

            self.screen = "main"
            self.normalize_selection()

            self.render_static()
            self.render_dynamic()
            self.update_visibility()

            self.game.canvas.tag_raise(
                "menu"
            )

    def render_cell_screen(self):
        if not self.cell_text:
            return

        entries = self.get_phone_entries()
        main_font = self.game.ui_sprites.main_font

        if entries:
            self.cell_selected = min(
                self.cell_selected,
                len(entries) - 1,
            )
        else:
            self.cell_selected = 0

        for i, text in enumerate(
            self.cell_text
        ):
            if i < len(entries):
                _, name = entries[i]

                image = main_font.render(
                    str(name)
                )
                self.cell_font_images[i] = image

                self.game.canvas.itemconfigure(
                    text,
                    image=image,
                )
            else:
                self.cell_font_images.pop(
                    i,
                    None,
                )
                self.game.canvas.itemconfigure(
                    text,
                    image="",
                )

    def render_stat_screen(self):

        if not self.stat_text:
            return

        main_font = self.game.ui_sprites.main_font

        stats = self.get_stat_data()

        name = str(stats["name"])
        lv = int(stats["lv"])
        hp = int(stats["hp"])
        max_hp = int(stats["max_hp"])

        at = int(stats["at"])
        weapon_strength = int(
            stats["weapon_strength"]
        )

        df = int(stats["df"])
        armor_defense = int(
            stats["armor_defense"]
        )

        weapon_id = int(stats["weapon"])
        armor_id = int(stats["armor"])

        gold = int(stats["gold"])
        xp = int(stats["xp"])

        self.kris_preservation_society = int(
            stats["kris_preservation_society"]
        )

        # --------------------------------------------------
        # Equipment names
        # --------------------------------------------------

        weapon_name = LW_WEAPON_NAMES.get(
            weapon_id,
            "None"
        )

        armor_name = LW_ARMOR_NAMES.get(
            armor_id,
            "None"
        )

        # --------------------------------------------------
        # EXP until next LV
        # --------------------------------------------------

        if lv >= 20:
            next_level = 0

        else:
            threshold = EXP_THRESHOLDS.get(
                lv
            )

            if threshold is None:
                next_level = 0
            else:
                next_level = threshold - xp

        # --------------------------------------------------
        # Main STAT text
        # --------------------------------------------------

        values = {
            "name": f"\"{name}\"",

            "lv": f"LV  {lv}",
            "hp": f"HP  {hp} / {max_hp}",

            "at": (
                f"AT  {at} "
                f"({weapon_strength})"
            ),

            "df": (
                f"DF  {df} "
                f"({armor_defense})"
            ),

            "weapon": (
                f"WEAPON: {weapon_name}"
            ),

            "armor": (
                f"ARMOR: {armor_name}"
            ),

            "money": f"MONEY: {gold}",

            "exp": f"EXP: {xp}",
            "next": f"NEXT: {next_level}",

            "special_1": "",
            "special_2": "",
        }

        # --------------------------------------------------
        # Top-right special text
        #
        # GML:
        #
        # if string_length(lcharname) >= 7:
        #     ???
        #
        # else if flag[914] > 0:
        #     Since
        #     Chapter X
        # --------------------------------------------------

        if len(name) >= 7:

            values["special_1"] = "???"

        elif self.kris_preservation_society > 0:

            values["special_1"] = "Since"
            values["special_2"] = (
                f"Chapter {self.kris_preservation_society}"
            )

        # --------------------------------------------------
        # Render
        # --------------------------------------------------

        for key, value in values.items():

            if value:

                image = main_font.render(
                    value
                )

                self.stat_font_images[key] = image

                self.game.canvas.itemconfigure(
                    self.stat_text[key],
                    image=image
                )

            else:

                self.stat_font_images.pop(
                    key,
                    None
                )

                self.game.canvas.itemconfigure(
                    self.stat_text[key],
                    image=""
                )

    # ======================================================
    # RENDERING
    # ======================================================

    def render_static(self):

        if not self.canvas_items:
            self.create_widgets()
        main_font = self.game.ui_sprites.main_font

        for action, text in zip(
            ("USE", "INFO", "DROP"),
            self.action_text
        ):

            image = main_font.render(
                action
            )

            self.action_font_images[action] = image

            self.game.canvas.itemconfigure(
                text,
                image=image
            )

        # --------------------------------------------------
        # Refresh main menu sprite
        # --------------------------------------------------

        menu_photo = self.game.ui_sprites.get(
            "menu_box"
        )

        self.game.canvas.itemconfigure(
            self.menu_sprite,
            image=menu_photo
        )

        # --------------------------------------------------
        # Refresh item menu sprite
        # --------------------------------------------------

        item_menu_photo = self.game.ui_sprites.get(
            "menu_box_item"
        )

        self.game.canvas.itemconfigure(
            self.menu_sprite_item,
            image=item_menu_photo
        )

        # --------------------------------------------------
        # Refresh stat menu sprite
        # --------------------------------------------------

        stat_menu_photo = self.game.ui_sprites.get(
            "menu_box_stat"
        )

        self.game.canvas.itemconfigure(
            self.menu_sprite_stat,
            image=stat_menu_photo
        )

        self.render_stat_screen()
        self.render_cell_screen()

        # --------------------------------------------------
        # Refresh cursor
        # --------------------------------------------------

        self.refresh_cursor()

        # --------------------------------------------------
        # Refresh main menu option glyphs
        # --------------------------------------------------

        for i, (option, text) in enumerate(
            zip(
                self.options,
                self.option_text
            )
        ):

            color = (
                "white"
                if self.option_enabled(i)
                else "gray"
            )

            image = main_font.render(
                option,
                color=color
            )

            self.game.canvas.itemconfigure(
                text,
                image=image
            )

        # --------------------------------------------------
        # Refresh item text
        # --------------------------------------------------

        inventory = self.get_inventory()

        main_font = self.game.ui_sprites.main_font

        for i, text in enumerate(
            self.item_text
        ):

            if i < len(inventory):

                item_name = self.get_item_name(
                    inventory[i]
                )

                image = main_font.render(
                    item_name
                )

                self.main_font_images[i] = image

                self.game.canvas.itemconfigure(
                    text,
                    image=image
                )

            else:

                self.game.canvas.itemconfigure(
                    text,
                    image=""
                )

        # --------------------------------------------------
        # Position everything
        # --------------------------------------------------

        self.layout_widgets()

        # Keep visibility correct when this method is called
        # during fullscreen resizing.
        if self.visible:
            self.update_visibility()

    def render_dynamic(self):

        if self.cursor is None:
            return

        self.normalize_selection()

        # --------------------------------------------------
        # Soul cursor
        # --------------------------------------------------

        if self.screen == "main":

            cursor_x = 28
            cursor_y = (
                98
                + self.selected * 18
            )

        elif self.screen == "item":

            cursor_x = 104
            cursor_y = (
                44
                + self.item_selected * 16
            )

        elif self.screen == "item_action":

            cursor_x, cursor_y = (
                ITEM_ACTION_CURSOR_POSITIONS[
                    self.item_action_selected
                ]
            )

        elif self.screen == "cell":
            entries = self.get_phone_entries()

            if not entries:
                self.game.canvas.itemconfigure(
                    self.cursor,
                    state="hidden",
                )
                self.render_cell_screen()
                self.game.canvas.tag_raise(
                    "menu"
                )
                return

            self.cell_selected = min(
                self.cell_selected,
                len(entries) - 1,
            )

            cursor_x = 104
            cursor_y = (
                44
                + self.cell_selected * 16
            )
            self.render_cell_screen()

        elif self.screen == "stat":

            # STAT has no cursor, but its values may have
            # changed while the menu is open.
            self.render_stat_screen()

            self.game.canvas.tag_raise(
                "menu"
            )

            return

        else:
            return

        self.game.canvas.itemconfigure(
            self.cursor,
            state="normal",
        )

        x, y = self.game.ui_to_screen(
            cursor_x,
            cursor_y
        )

        self.game.canvas.coords(
            self.cursor,
            x,
            y
        )

        # --------------------------------------------------
        # Keep main menu options current
        # --------------------------------------------------

        main_font = self.game.ui_sprites.main_font

        for i, (option, text) in enumerate(
            zip(
                self.options,
                self.option_text
            )
        ):

            color = (
                "white"
                if self.option_enabled(i)
                else "gray"
            )

            image = main_font.render(
                option,
                color=color
            )

            self.game.canvas.itemconfigure(
                text,
                image=image
            )

        # --------------------------------------------------
        # Keep inventory current
        # --------------------------------------------------

        inventory = self.get_inventory()

        for i, text in enumerate(
            self.item_text
        ):

            if i < len(inventory):

                item_name = self.get_item_name(
                    inventory[i]
                )

                image = main_font.render(
                    item_name
                )

                self.main_font_images[i] = image

                self.game.canvas.itemconfigure(
                    text,
                    image=image
                )

            else:

                self.game.canvas.itemconfigure(
                    text,
                    image=""
                )

        self.game.canvas.tag_raise(
            "menu"
        )