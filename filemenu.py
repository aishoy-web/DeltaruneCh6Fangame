'''The file menu class
      -This class is responsible for drawing the file menu and handling user input for it. 
      -there should be three horizontal slots arranged vertically, with
      -a set of options the player can interact with (new,)
'''

class FileMenu:
    def __init__(self, game):
        self.game = game
        self.canvas = game.canvas

        # Keep PhotoImage references alive
        self.small_font_images = {}
        self.main_font_images = {}
        
    
    def create_widgets(self):
        # slots
        self.slot1_sprite = self.game.canvas.create_image(
                    0,
                    0,
                    anchor="nw",
                    image=self.game.ui_sprites.get("status_box"),
                    state="hidden",
                    tags=("hud",)
                )
        
        self.slot2_sprite = self.game.canvas.create_image(
                    0,
                    0,
                    anchor="nw",
                    image=self.game.ui_sprites.get("status_box"),
                    state="hidden",
                    tags=("hud",)
                )
        
        self.slot3_sprite = self.game.canvas.create_image(
                    0,
                    0,
                    anchor="nw",
                    image=self.game.ui_sprites.get("status_box"),
                    state="hidden",
                    tags=("hud",)
                )
        
        # Text
        
        main_font = self.game.ui_sprites.main_font
    
        self.main_font_images["Please select a file."] = (
            main_font.render("Please select a file.")
        )
    
        self.main_font_images[self.game.slot1.name] = (
            main_font.render(self.game)
        )
        
        #call to get text functions updated
        self.update_text()
    
    def update_text(self):
        
        self.layout_widgets()
        
    def layout_widgets(self):
    
        #x and y positions for the slots
        #currently not adjusting for screen size, TODO: fix this
        slot1_x = 100
        slot1_y = 100
        slot2_x = 100
        slot2_y = 500
        slot3_x = 100
        slot3_y = 900
        
        self.slot1_sprite = self.game.canvas.create_image(
                    slot1_x,
                    slot1_y,
                    anchor="nw",
                    image=self.game.ui_sprites.get("dialogue_box"),
                )
        
        self.slot2_sprite = self.game.canvas.create_image(
                    slot2_x,
                    slot2_y,
                    anchor="nw",
                    image=self.game.ui_sprites.get("dialogue_box"),
                )
        
        self.slot3_sprite = self.game.canvas.create_image(
                    slot3_x,
                    slot3_y,
                    anchor="nw",
                    image=self.game.ui_sprites.get("dialogue_box"),
                )

    def render_static(self):
        self.update_text()

        self.layout_widgets()