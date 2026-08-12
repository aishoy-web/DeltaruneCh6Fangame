from pathlib import Path
from PIL import Image, ImageTk
from animated_sprite import AnimatedSprite
BASE_DIR = Path(__file__).parent
sprite_path = BASE_DIR/"sprites"/"player"/"spr_krisd"/"spr_krisd_0.png"
sprite_sheet_path = BASE_DIR/"sprites"/"player"/"kris_spritesheet_1+2.png"
class Player:
    def __init__(self, game):
        self.game = game
        self.room = game.room
        self.x = 160
        self.y = 110
        self.walk_speed = 3 # Controls walking speed
        self.run_speed = self.walk_speed * 1.75
        self.speed = 0
        self.acceleration = 0.4
        self.photo = None
        self.canvas_sprite = None
        self.animation = AnimatedSprite(
            sprite_sheet_path,
            cell_width=24,
            cell_height=44,
            sprite_width=19,
            sprite_height=37,
            sheet_offset_x=7,
            sheet_offset_y = 24,
            animations={
                "down": (0, 0, 4),
                "left": (1, 0, 4),
                "right": (2, 0, 4),
                "up": (3, 0, 4)},
                animation_speed = 6.5
        )
        self.walk_animation_speed = 6.5
        self.run_animation_speed = self.walk_animation_speed * .5
        self.hitbox_width = 15
        self.hitbox_height = 6
        self.hitbox_offset_x = 2.5
        self.hitbox_offset_y = 32
        self.last_scale = None
        self.facing = "down"
        if self.game.debug_mode:
            self.hitbox_debug = self.game.canvas.create_rectangle(
                0,0,0,0,
                outline = "blue",
                width = 2,
                tags = "player_debug")
        else:
            self.hitbox_debug = None
    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        frame = self.animation.get_frame()
        width = frame.width
        height = frame.height
        if self.x < 0:
            self.try_exit("left")
        elif self.x > self.game.game_width - width:
            self.try_exit("right")
        if self.y < 0:
            self.try_exit("up")
        elif self.y > self.game.game_height - height:
            self.try_exit("down")
        self.render()
    def try_exit(self, direction):
        if direction in self.game.room.exits:
            next_room = self.game.room.exits[direction]
            self.game.load_room(next_room)
    def teleport(self,x,y):
        self.x = x
        self.y = y
    # def set_sprinting(self, sprinting):
    #     if sprinting:
    #         self.speed = self.run_speed
    #     else:
    #         self.speed = self.walk_speed
    def move_left(self):
        self.facing = "left"
        new_x = self.x -self.speed
        if self.can_move_to(new_x, self.y):
            self.x = new_x

    def move_right(self):
        self.facing = "right"
        new_x = self.x + self.speed
        if self.can_move_to(new_x, self.y):
            self.x = new_x

    def move_up(self):
        self.facing = "up"
        new_y = self.y - self.speed
        if self.can_move_to(self.x, new_y):
            self.y = new_y

    def move_down(self):
        self.facing = "down"
        new_y = self.y + self.speed
        if self.can_move_to(self.x, new_y):
            self.y = new_y
    
    def get_interaction_box(self):
        size = 16 # Change this to increase or decrease the size of the interaction box
        left, top, right, bottom = self.get_hitbox(self.x, self.y)
        if self.facing == "up":
            return (
                left,
                top - size,
                right,
                top,)

        elif self.facing == "down":
            return (
                left,
                bottom,
                right,
                bottom + size,)

        elif self.facing == "left":
            return (
                left - size,
                top,
                right,
                bottom,)

        else:  # right
            return (
                right,
                top,
                right + size,
                bottom,)
    def render(self):
        frame = self.animation.get_frame()
        scaled = frame.resize((int(frame.width * self.game.scale),int(frame.height * self.game.scale)),Image.Resampling.NEAREST)
        self.photo = ImageTk.PhotoImage(scaled)
        canvas_x, canvas_y = self.game.game_to_screen(self.x, self.y)
        if self.canvas_sprite is None:
            self.canvas_sprite = self.game.canvas.create_image(
                    canvas_x,
                    canvas_y,
                    image=self.photo,
                    anchor="nw")
        else:
            self.game.canvas.coords(
                self.canvas_sprite,
                canvas_x,
                canvas_y)
            self.game.canvas.itemconfig(
                self.canvas_sprite,
                image=self.photo)    
        if self.hitbox_debug is not None:
            self.game.canvas.coords(
                self.hitbox_debug,
                canvas_x + self.hitbox_offset_x * self.game.scale,
                canvas_y + self.hitbox_offset_y * self.game.scale,
                canvas_x + (self.hitbox_offset_x + self.hitbox_width) * self.game.scale,
                canvas_y + (self.hitbox_offset_y + self.hitbox_height) * self.game.scale,)
        self.game.update_debug_hud()
    def can_move_to(self, new_x, new_y):
        player_left, player_top, player_right, player_bottom = self.get_hitbox(new_x, new_y)

        for left, top, right, bottom in self.room.collisions:
            if (
                player_right > left and
                player_left < right and
                player_bottom > top and
                player_top < bottom
            ):
                return False

        return True
    def is_touching_exit(self, exit):
        player_left, player_top, player_right, player_bottom = self.get_hitbox()

        exit_left = exit.x
        exit_top = exit.y
        exit_right = exit.x + exit.width
        exit_bottom = exit.y + exit.height

        return (
            player_right > exit_left and
            player_left < exit_right and
            player_bottom > exit_top and
            player_top < exit_bottom)
    def get_hitbox(self, x=None, y=None):
        if x is None:
            x = self.x
        if y is None:
            y = self.y

        left = x + self.hitbox_offset_x
        top = y + self.hitbox_offset_y
        right = left + self.hitbox_width
        bottom = top + self.hitbox_height

        return left, top, right, bottom