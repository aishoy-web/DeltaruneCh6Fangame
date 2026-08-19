class HUD:
    def __init__(self, game):
        self.game = game

        # Status box dimensions in native UI pixels
        self.status_x = 16
        self.status_y = 161.5

        self.status_width = 71
        self.status_height = 55

        # Text positioning
        self.text_padding = 7

        # Canvas items
        self.canvas_items = []

        self.status_sprite = None

        # Kris uses the normal installed font
        self.name_text = None

        # Small bitmap-font items
        self.level_label = None
        self.level_value = None

        self.hp_label = None
        self.hp_value = None

        self.money_label = None
        self.money_value = None

        # Keep PhotoImage references alive
        self.small_font_images = {}

        # Player information
        self.level = 1
        self.hp = 20
        self.max_hp = 20
        self.money = 2

        self.create_widgets()

    def create_widgets(self):

        # --------------------------------
        # Status box
        # --------------------------------

        self.status_sprite = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.game.ui_sprites.get("status_box"),
            state="hidden",
            tags=("hud",)
        )

        # --------------------------------
        # Kris' name
        #
        # IMPORTANT:
        # This remains Determination Mono Web.
        # --------------------------------

        self.name_text = self.game.canvas.create_text(
            0,
            0,
            anchor="nw",
            text="Kris",
            fill="white",
            font=(
                "Determination Mono Web",
                42
            ),
            state="hidden",
            tags=("hud",)
        )

        # --------------------------------
        # Small bitmap font
        # --------------------------------

        self.level_label = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=("hud",)
        )

        self.level_value = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=("hud",)
        )

        self.hp_label = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=("hud",)
        )

        self.hp_value = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=("hud",)
        )

        self.money_label = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=("hud",)
        )

        self.money_value = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=("hud",)
        )

        self.canvas_items.extend([
            self.status_sprite,
            self.name_text,
            self.level_label,
            self.level_value,
            self.hp_label,
            self.hp_value,
            self.money_label,
            self.money_value
        ])

        self.update_text()

    def update_text(self):

        # --------------------------------
        # Generate small-font images
        # --------------------------------

        small_font = self.game.ui_sprites.small_font
        #main_font = self.game.ui_sprites.main_font

        self.small_font_images["LV"] = (
            small_font.render("LV")
        )

        self.small_font_images["level"] = (
            small_font.render(
                str(self.level)
            )
        )

        self.small_font_images["HP"] = (
            small_font.render("HP")
        )

        self.small_font_images["hp"] = (
            small_font.render(
                f"{self.hp}/{self.max_hp}"
            )
        )

        self.small_font_images["money_label"] = (
            small_font.render("$")
        )

        self.small_font_images["money"] = (
            small_font.render(
                str(self.money)
            )
        )

        # --------------------------------
        # Update Canvas images
        # --------------------------------

        self.game.canvas.itemconfigure(
            self.level_label,
            image=self.small_font_images["LV"]
        )

        self.game.canvas.itemconfigure(
            self.level_value,
            image=self.small_font_images["level"]
        )

        self.game.canvas.itemconfigure(
            self.hp_label,
            image=self.small_font_images["HP"]
        )

        self.game.canvas.itemconfigure(
            self.hp_value,
            image=self.small_font_images["hp"]
        )

        self.game.canvas.itemconfigure(
            self.money_label,
            image=self.small_font_images["money_label"]
        )

        self.game.canvas.itemconfigure(
            self.money_value,
            image=self.small_font_images["money"]
        )

        self.layout_widgets()

    def update_position(self):

        player_center_y = (
            self.game.player.y +
            self.game.player.animation.sprite_height / 2
        )

        viewport_y = (
            player_center_y -
            self.game.camera_y
        )

        # Move to the bottom when Kris is in the bottom 35%
        if viewport_y <= self.game.viewport_height * 0.65:
            new_y = 26
        else:
            new_y = 161

        if new_y != self.status_y:
            self.status_y = new_y
            self.layout_widgets()

    def layout_widgets(self):

        # --------------------------------
        # Status box
        # --------------------------------

        x, y = self.game.ui_to_screen(
            self.status_x,
            self.status_y
        )

        self.game.canvas.coords(
            self.status_sprite,
            x,
            y
        )

        # --------------------------------
        # Kris
        # --------------------------------

        name_x = self.status_x + 6 #Done, no touchy
        name_y = self.status_y + 4

        name_x, name_y = self.game.ui_to_screen(
            name_x,
            name_y
        )

        self.game.canvas.coords(
            self.name_text,
            name_x,
            name_y
        )

        # --------------------------------
        # Small-font stat positions
        #
        # These are native 320x240 UI coordinates.
        # --------------------------------

        # LV
        lv_x = self.status_x + 7
        lv_y = self.status_y + 24

        # LV value
        lv_value_x = self.status_x + 25
        lv_value_y = self.status_y + 24

        # HP
        hp_x = self.status_x + 7
        hp_y = self.status_y + 33

        # HP value
        hp_value_x = self.status_x + 25
        hp_value_y = self.status_y + 33

        # $
        money_x = self.status_x + 7
        money_y = self.status_y + 42

        # Money value
        money_value_x = self.status_x + 24
        money_value_y = self.status_y + 42

        # --------------------------------
        # Convert to screen coordinates
        # --------------------------------

        lv_x, lv_y = self.game.ui_to_screen(
            lv_x,
            lv_y
        )

        lv_value_x, lv_value_y = self.game.ui_to_screen(
            lv_value_x,
            lv_value_y
        )

        hp_x, hp_y = self.game.ui_to_screen(
            hp_x,
            hp_y
        )

        hp_value_x, hp_value_y = self.game.ui_to_screen(
            hp_value_x,
            hp_value_y
        )

        money_x, money_y = self.game.ui_to_screen(
            money_x,
            money_y
        )

        money_value_x, money_value_y = self.game.ui_to_screen(
            money_value_x,
            money_value_y
        )

        # --------------------------------
        # Position small-font images
        # --------------------------------

        self.game.canvas.coords(
            self.level_label,
            lv_x,
            lv_y
        )

        self.game.canvas.coords(
            self.level_value,
            lv_value_x,
            lv_value_y
        )

        self.game.canvas.coords(
            self.hp_label,
            hp_x,
            hp_y
        )

        self.game.canvas.coords(
            self.hp_value,
            hp_value_x,
            hp_value_y
        )

        self.game.canvas.coords(
            self.money_label,
            money_x,
            money_y
        )

        self.game.canvas.coords(
            self.money_value,
            money_value_x,
            money_value_y
        )

    def render_static(self):

        # --------------------------------
        # Refresh scaled status sprite
        # --------------------------------

        status_photo = self.game.ui_sprites.get(
            "status_box"
        )

        self.game.canvas.itemconfigure(
            self.status_sprite,
            image=status_photo
        )

        # --------------------------------
        # Refresh small font
        #
        # Important when fullscreen scale changes.
        # --------------------------------

        self.update_text()

        # --------------------------------
        # Position HUD
        # --------------------------------

        self.layout_widgets()

        self.game.canvas.tag_raise("hud")

    def open(self):

        for item in self.canvas_items:
            self.game.canvas.itemconfigure(
                item,
                state="normal"
            )

        self.game.canvas.tag_raise("hud")

    def close(self):

        for item in self.canvas_items:
            self.game.canvas.itemconfigure(
                item,
                state="hidden"
            )