from pathlib import Path
from PIL import Image, ImageTk
BASE_DIR = Path(__file__).parent
sprite_path = BASE_DIR/"sprites"/"player"/"susie_test_new.png"
class Player:
    def __init__(self, game, room):
        self.game = game
        self.x = 320
        self.y = 220
        self.speed = 6.5
        self.image = Image.open(sprite_path)
        self.photo = ImageTk.PhotoImage(self.image)
        self.game.player_label.config(image=self.photo)
        self.draw()
    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        if self.x < 0:
            self.try_exit("left")
        elif self.x > 900:
            self.try_exit("right")
        self.draw()
    def try_exit(self, direction):
        if direction in self.game.current_room.exits:
            next_room = self.game.current_room.exits[direction]
            self.game.load_room(next_room)
    def move_left(self, isSprintHeld):
        # is this move allowed? if yes, continue, if not, get out and don't do anything below
        # isMoveAllowed = self.boundary_checker.check_boundaries(self, room, 'left')
        # if isMoveAllowed:
            if isSprintHeld:
                self.move(-self.speed*2, 0)
            else:
                self.move(-self.speed, 0)

    def move_right(self):
        self.move(self.speed, 0)

    def move_up(self):
        self.move(0, -self.speed)

    def move_down(self):
        self.move(0, self.speed)
    # def update(self):
    #     if self.left_pressed:
    #         self.player.move(-self, Player.speed, 0)
    #     if self.right_pressed:
    #         self.player.move(self, Player.speed, 0)
    #     self.root.after(50, self.update)
    def draw(self):
        self.game.player_label.place(x=self.x, y=self.y)