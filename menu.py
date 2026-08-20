import pygame
from pathlib import Path
from PIL import Image, ImageTk


BASE_DIR = Path(__file__).resolve().parent

cursor_path = (
    BASE_DIR
    / "sprites"
    / "player"
    / "player_red_soul"
    / "spr_heartsmall.png"
)


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
        self.item_menu_sprite = None
        self.cursor = None

        self.item_text = []
        self.action_text = []

        # ==================================================
        # Menu state
        # ==================================================

        self.visible = False

        # "main" = ITEM / STAT / CELL
        # "item" = inventory screen
        self.screen = "main"

        self.selected = 0
        self.item_selected = 0

        self.options = [
            "ITEM",
            "STAT",
            "CELL"
        ]

        # Maximum number of inventory entries currently
        # displayed in the Item window.
        self.max_visible_items = 10

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
        Convert an inventory entry into the text displayed
        in the Item menu.
        """

        if isinstance(item, dict):
            return str(
                item.get(
                    "name",
                    ""
                )
            )

        return str(item)

    def has_items(self):
        return len(self.get_inventory()) > 0

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

        self.item_menu_sprite = self.game.canvas.create_image(
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

            text = self.game.canvas.create_text(
                0,
                0,
                text=option,
                anchor="nw",
                font=(
                    "Determination Mono Web",
                    45
                ),
                fill="white",
                state="hidden",
                tags=("menu",)
            )

            self.option_text.append(text)

        # --------------------------------------------------
        # Inventory item text
        # --------------------------------------------------

        for _ in range(self.max_visible_items):

            text = self.game.canvas.create_text(
                0,
                0,
                text="",
                anchor="nw",
                font=(
                    "Determination Mono Web",
                    45
                ),
                fill="white",
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

            text = self.game.canvas.create_text(
                0,
                0,
                text=action,
                anchor="nw",
                font=(
                    "Determination Mono Web",
                    45
                ),
                fill="white",
                state="hidden",
                tags=("menu",)
            )

            self.action_text.append(text)

        self.canvas_items.extend(
            [
                self.menu_sprite,
                self.item_menu_sprite,
                self.cursor,
                *self.option_text,
                *self.item_text,
                *self.action_text
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
                41,
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
            self.item_menu_sprite,
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
                    115,
                    40 + i * 16
                )

                self.game.canvas.coords(
                    text,
                    x,
                    y
                )

                self.game.canvas.itemconfigure(
                    text,
                    text=self.get_item_name(
                        inventory[i]
                    )
                )

            else:

                self.game.canvas.itemconfigure(
                    text,
                    text=""
                )

        # --------------------------------------------------
        # Bottom actions
        # --------------------------------------------------

        action_positions = [
            (115, 180),
            (163, 180),
            (220, 180)
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
            self.screen == "item"
        )

        self.game.canvas.itemconfigure(
            self.item_menu_sprite,
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
            state="normal"
        )

    # ======================================================
    # OPEN / CLOSE
    # ======================================================

    def open(self):

        self.visible = True
        self.screen = "main"
        self.selected = 0
        self.item_selected = 0

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

        start = self.selected

        for _ in range(len(self.options)):

            self.selected = (
                self.selected - 1
            ) % len(self.options)

            if self.option_enabled(
                self.selected
            ):
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

        start = self.selected

        for _ in range(len(self.options)):

            self.selected = (
                self.selected + 1
            ) % len(self.options)

            if self.option_enabled(
                self.selected
            ):
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

            # STAT and CELL will be implemented later.
            return

        # --------------------------------------------------
        # Item menu
        # --------------------------------------------------

        if self.screen == "item":

            # Item actions will be implemented next.
            #
            # For now, pressing Z while an item is selected
            # simply plays the selection sound.
            inventory = self.get_inventory()

            if inventory:
                self.menu_select.play()

    def back(self):

        if not self.visible:
            return

        if self.screen == "item":

            self.screen = "main"
            self.normalize_selection()

            # self.menu_move.play() # For some reason, backing out of ITEM doesn't play menu_move, but STAT and CELL will(?)

            self.render_static()
            self.render_dynamic()
            self.update_visibility()

            self.game.canvas.tag_raise(
                "menu"
            )

    # ======================================================
    # RENDERING
    # ======================================================

    def render_static(self):

        if not self.canvas_items:
            self.create_widgets()

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
            self.item_menu_sprite,
            image=item_menu_photo
        )

        # --------------------------------------------------
        # Refresh cursor
        # --------------------------------------------------

        self.refresh_cursor()

        # --------------------------------------------------
        # Refresh option colors
        # --------------------------------------------------

        for i, text in enumerate(
            self.option_text
        ):

            if self.option_enabled(i):
                fill = "white"
            else:
                fill = "gray"

            self.game.canvas.itemconfigure(
                text,
                fill=fill
            )

        # --------------------------------------------------
        # Refresh item text
        # --------------------------------------------------

        inventory = self.get_inventory()

        for i, text in enumerate(
            self.item_text
        ):

            if i < len(inventory):

                self.game.canvas.itemconfigure(
                    text,
                    text=self.get_item_name(
                        inventory[i]
                    ),
                    fill="white"
                )

            else:

                self.game.canvas.itemconfigure(
                    text,
                    text=""
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

        else:

            cursor_x = 104 #These values are for when the soul cursor is in ITEM.
            cursor_y = (
                44
                + self.item_selected * 16 # Test 
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
        # Keep ITEM's disabled state current
        # --------------------------------------------------

        for i, text in enumerate(
            self.option_text
        ):

            self.game.canvas.itemconfigure(
                text,
                fill=(
                    "white"
                    if self.option_enabled(i)
                    else "gray"
                )
            )

        # --------------------------------------------------
        # Keep inventory current
        # --------------------------------------------------

        inventory = self.get_inventory()

        for i, text in enumerate(
            self.item_text
        ):

            if i < len(inventory):

                self.game.canvas.itemconfigure(
                    text,
                    text=self.get_item_name(
                        inventory[i]
                    )
                )

            else:

                self.game.canvas.itemconfigure(
                    text,
                    text=""
                )

        self.game.canvas.tag_raise(
            "menu"
        )