from PIL import Image
class AnimatedSprite:
    def __init__(self,
                 sprite_sheet_path,
                 cell_width = 24,
                 cell_height=44,
                 sprite_width = 19,
                 sprite_height = 37,
                 sheet_offset_x=7,
                 sheet_offset_y=24,
                 animations = None,
                 animation_speed=7):
        if animations is None:
            animations = {"down": (0, 0, 4),"left": (1, 0, 4),"right": (2, 0, 4),"up": (3, 0, 4)}
        self.sheet = Image.open(sprite_sheet_path).convert("RGBA")
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.sprite_width = sprite_width
        self.sprite_height = sprite_height
        self.sheet_offset_x = sheet_offset_x
        self.sheet_offset_y = sheet_offset_y    
        self.animation_speed = animation_speed
        self.animations = {}
        transparent_color = (195,134,255) # Comes from the spritesheet background, don't touch
        for name, (row, start_col, frame_count) in animations.items():
            frames = []
            for col in range(frame_count):
                left =  left = self.sheet_offset_x + (start_col + col) * self.cell_width
                top = self.sheet_offset_y + row * self.cell_height
                frame = self.sheet.crop((
                    left,
                    top,
                    left + self.sprite_width,
                    top + self.sprite_height,
                ))
                frame = frame.convert("RGBA")
                pixels = frame.load()
                for y in range(frame.height):
                    for x in range(frame.width):
                        r,g,b,a = pixels[x,y]
                        if (r,g,b) == transparent_color:
                            pixels[x,y] = (0,0,0,0)
                frames.append(frame)
            self.animations[name] = frames
        #changed to instead take the first animation in the dict, which allows it to be more reusable
        #hurrah for reuseable code! (and also for not having to make a new class for every single sprite)
        self.current_animation = next(iter(self.animations))
        self.current_frame = 0
        self.timer = 0
        self.rest_frames = (0,2)
        self.stop_at_rest_frame = False
        self.finish_when_cycle_ends = False
        self.finish_rest_frame = 0
        self.stop_target_rest_frame = 0
        self.playing = False
    def play(self, animation_name):
        if animation_name not in self.animations:
            raise ValueError(f"Unknown animation: {animation_name}")

        # Starting movement again cancels any pending stop.
        self.stop_at_rest_frame = False
        self.finish_when_cycle_ends = False

        if animation_name != self.current_animation:
            self.current_animation = animation_name
            self.current_frame = 0
            self.timer = 0

        if not self.playing:
            self.current_frame = 1
            self.timer = 0

        self.playing = True
    def update(self):
        if not self.playing:
            return
        self.timer += 1
        if self.timer >= self.animation_speed:
            self.timer = 0

            frame_count = len(
                self.animations[self.current_animation]
            )

            self.current_frame += 1

            if self.current_frame >= frame_count:
                self.current_frame = 0

                if self.finish_when_cycle_ends:
                    self.playing = False
                    self.finish_when_cycle_ends = False
                    self.current_frame = self.finish_rest_frame
                    return

            if (
                self.stop_at_rest_frame
                and self.current_frame == self.stop_target_rest_frame
            ):
                self.playing = False
                self.stop_at_rest_frame = False
        # print(self.current_animation, self.current_frame) #Uncomment to see which frames of animation are playing.
    def get_frame(self):
        return self.animations[self.current_animation][self.current_frame]
    def finish_at_rest_frame(self):
        if self.current_frame in (0, 1):
            self.current_frame = 0
        else:
            self.current_frame = 2
        self.playing = False
        self.timer = 0
    def stop(self):
        self.playing = False
        self.current_frame = 0
        self.timer = 0
        self.stop_at_rest_frame = False
        self.finish_when_cycle_ends = False
        self.finish_rest_frame = 0
        self.stop_target_rest_frame = 0
    def start(self):
        self.playing = True
    def is_finished(self):
        return(
            self.current_frame == len(self.animations[self.current_animation]) - 1
            and self.timer == 0
        )
    def finish_current_cycle(self):
        if not self.playing:
            return
        if self.current_frame in (0, 1):
            self.finish_rest_frame = 0
        else:
            self.finish_rest_frame = 2
        self.finish_when_cycle_ends = True
    def stop_at_next_rest_frame(self):
        if not self.playing:
            return

        if self.current_frame == 0:
            # Already on a rest frame.
            self.playing = False
            self.timer = 0
            return

        elif self.current_frame == 1:
            # Finish the step by advancing to frame 2.
            self.stop_target_rest_frame = 2

        elif self.current_frame == 2:
            # Already on a rest frame.
            self.playing = False
            self.timer = 0
            return

        elif self.current_frame == 3:
            # Finish the step by advancing through the cycle to frame 0.
            self.stop_target_rest_frame = 0

        self.stop_at_rest_frame = True