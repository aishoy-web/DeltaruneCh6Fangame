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
    
        self.main_font_images[self.game.player.name] = (
            main_font.render(self.game.player.name)
        )