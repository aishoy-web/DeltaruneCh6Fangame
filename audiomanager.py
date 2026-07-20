import pygame
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
class AudioManager:
    def __init__(self):
        pygame.mixer.init()
        self.current_music = None
        self.music_volume = 0.5
    def play_music(self, filename, loop=True):
        music_path = BASE_DIR / "mus" / filename
        if self.current_music == filename:
            return  # Don't restart the same song
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(self.music_volume)
        loops = -1 if loop else 0
        pygame.mixer.music.play(loops)
        self.current_music = filename
    def stop_music(self):
        pygame.mixer.music.stop()
        self.current_music = None
    def fade_out(self, duration=1000):
        pygame.mixer.music.fadeout(duration)
    def change_music(self, filename):
        if self.current_music == filename:
            return
        pygame.mixer.music.fadeout(500)
        self.game.root.after(
        500,
        lambda: self.play_music(filename))
    def play_sfx(self, filename):
        sound = pygame.mixer.Sound(
            BASE_DIR / "audio" / "sfx" / filename
        )
        sound.play()