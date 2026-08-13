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
        
        # initialize scale basic scale
        width = self.game.canvas.winfo_width()
        height = self.game.canvas.winfo_height()
        
        if width < 2 or height < 2:
            width = self.game.root.winfo_screenwidth()
            height = self.game.root.winfo_screenheight()
            
        self.scale = min(width / self.game.viewport_width, height / self.game.viewport_height)

        self.selected = 0
        self.soul_scale = 0.5 # scale for the soul cursor to adjust its size.
        self.cursor_image = Image.open(cursor_path)
        self.cursor_photo = None
        self.refresh_size() # call refresh_size to initialize cursor_photo and option_text fonts 
    def refresh_size(self):
        # adjust the scale
        width = self.game.canvas.winfo_width()
        height = self.game.canvas.winfo_height()
        
        if width < 2 or height < 2:
            width = self.game.root.winfo_screenwidth()
            height = self.game.root.winfo_screenheight()    
            
        self.scale = min(width / self.game.viewport_width, height / self.game.viewport_height)
        # print(f"Scale: {self.scale}, Width: {width}, Height: {height}")  # Debugging line to check the scale and dimensions

        # scales, widths and the such.
        cursor_width = max(1, int(self.cursor_image.width * self.scale * self.soul_scale))
        cursor_height = max(1, int(self.cursor_image.height * self.scale * self.soul_scale))
        cursor_scaled = self.cursor_image.resize((cursor_width, cursor_height), Image.Resampling.NEAREST)
        self.cursor_photo = ImageTk.PhotoImage(cursor_scaled)

        # update the cursor image on the canvas if it exists (technically you might be able to fudge this to change the cursor image, dunno if we'll need it tho.)
        if self.cursor is not None:
            self.game.canvas.itemconfig(self.cursor, image=self.cursor_photo)

        # set font size based on scale
        font_size = max(12, int(12 * self.scale))
        for text in self.option_text:
            self.game.canvas.itemconfig(text, font=("Determination Mono Web", font_size))

        # set box size based on scale
        if self.box is not None:
            self.game.canvas.itemconfig(self.box, width=max(2, int(3 * self.scale)))
    def create_widgets(self):
        self.box = self.game.canvas.create_rectangle(
            0, 0, 0, 0,
            fill="black",
            outline="white",
            width=max(3, int(3 * self.scale)),
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
        self.refresh_size()
        self.layout_widgets()
    def render_dynamic(self):
        cursor_y = 98 + self.selected * 18 #Soul cursor, don't touch
        x, y = self.game.ui_to_screen(28, cursor_y)
        self.game.canvas.coords(self.cursor, x, y)
        for item in self.canvas_items:
            self.game.canvas.tag_raise(item)