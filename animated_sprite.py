from pathlib import Path
from PIL import Image
class AnimatedSprite:
    def __init__(self,
                 sprite_sheet_path,
                 frame_width,
                 frame_height,
                 animations,
                 animation_speed=8):
        self.sheet = Image.open(sprite_sheet_path).convert("RGBA")
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.animation_speed = animation_speed
        self.animations = {}
        for name, (row, frame_count) in animations.items():
            frames = []
            for col in range(frame_count):
                left = col * frame_width
                top = row * frame_height
                frame = self.sheet.crop((
                    left,
                    top,
                    left + frame_width,
                    top + frame_height,
                ))
                frames.append(frame)
            self.animations[name] = frames
        self.current_animation = "down"
        self.current_frame = 0
        self.timer = 0
        self.playing = False
    def play(self, animation_name):
        if animation_name not in self.animations:
            raise ValueError(f"Unknown animation: {animation_name}")
        self.playing = True
        if animation_name != self.current_animation:
            self.playing = True
            self.current_animation = animation_name
            self.current_frame = 0
            self.timer = 0
    def update(self):
        if not self.playing:
            return
        self.timer += 1
        if self.timer >= self.animation_speed:
            self.timer = 0
            frame_count = len(self.animations[self.current_animation])
            self.current_frame += 1
            self.current_frame %= frame_count
        # print(self.current_animation, self.current_frame) #Uncomment to see which frames of animation are playing.
    def get_frame(self):
        return self.animations[self.current_animation][self.current_frame]
    def stop(self):
        self.playing = False
        self.current_frame = 0
        self.timer = 0
    def start(self):
        self.playing = True