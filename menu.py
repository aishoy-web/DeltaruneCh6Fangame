from pathlib import Path
from PIL import Image, ImageTk
BASE_DIR = Path(__file__).resolve().parent
cursor_path = BASE_DIR/"sprites"/"player"/"player_red_soul"/"spr_heart_0.png"
class Menu:
    def __init__(self, game):
        self.game = game
        self.canvas_items = []
        self.option_text = []
        self.box = None
        self.cursor = None
        self.visible = False
        self.options = [
            "ITEM",
            "STAT",
            "CELL"
        ]

        self.selected = 0
        self.soul_scale = 2
        self.cursor_image = Image.open(cursor_path)
        self.cursor_scale = self.cursor_image.resize((int(self.cursor_image.width * self.game.scale*self.soul_scale),int(self.cursor_image.height * self.game.scale*self.soul_scale)), Image.Resampling.NEAREST)
        self.cursor_photo = ImageTk.PhotoImage(self.cursor_scale)
    def create_widgets(self):
        self.box = self.game.canvas.create_rectangle(
            0, 0, 0, 0,
            fill="black",
            outline="white",
            width=10,
        )
        self.canvas_items.append(self.box)
        self.game.canvas.itemconfigure(self.box, state="hidden")

        self.cursor = self.game.canvas.create_image(
            0, 0,
            image=self.cursor_photo,
            anchor="nw",
        )
        self.canvas_items.append(self.cursor)
        self.game.canvas.itemconfigure(self.cursor, state="hidden")

        for option in self.options:
            text = self.game.canvas.create_text(
                0,
                0,
                text=option,
                anchor="nw",
                font=("Determination Mono Web", 45),
                fill="white",
            )

            self.option_text.append(text)
            self.canvas_items.append(text)
            self.game.canvas.itemconfigure(text, state="hidden")
    def layout_widgets(self):
        x1, y1 = self.game.ui_to_screen(17, 85.5) #Box coords, don't touch
        x2, y2 = self.game.ui_to_screen(85.5, 157)
        self.game.canvas.coords(self.box, x1, y1, x2, y2)
        for i, text in enumerate(self.option_text):
                    x, y = self.game.ui_to_screen(41, 94 + i * 18) #Text coords, done
                    self.game.canvas.coords(text, x, y)
        self.render_dynamic()
    def open(self):
        self.visible = True
        self.render_dynamic()
        for item in self.canvas_items:
            self.game.canvas.itemconfigure(item, state = "normal")
    def close(self):
        self.visible = False
        for item in self.canvas_items:
            self.game.canvas.itemconfigure(item, state="hidden")
    def move_up(self):
        if self.selected > 0:
            self.selected -= 1
            # print(self.selected)
            self.render_dynamic()

    def move_down(self):
        if self.selected < len(self.options) -1:
            self.selected += 1
            # print(self.selected)
            self.render_dynamic()

    def render_static(self):
        if not self.canvas_items:
            self.create_widgets()
        self.layout_widgets()
    def render_dynamic(self):
        cursor_y = 98 + self.selected * 18 #Soul cursor, don't touch
        x, y = self.game.ui_to_screen(28, cursor_y)
        self.game.canvas.coords(self.cursor, x, y)