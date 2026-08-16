# responsible for extracting the spritesheet assets

from pathlib import Path
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).resolve().parent
SPRITESHEET_PATH = BASE_DIR / "sprites" / "ui" / "menu+HUD_spritesheet.png"


class UISpriteSheet:
    def __init__(self, game):
        self.game = game

        self.sheet = Image.open(SPRITESHEET_PATH).convert("RGBA")

        # Native-resolution sprites
        self.sprites = {
            "dialogue_box": self.sheet.crop((292, 19, 581, 95)),
            "status_box": self.sheet.crop((292, 119, 363, 174)),
            "menu_box": self.sheet.crop((292, 177, 363, 251)),
        }

        # Optional calibrated UI dimensions.
        #
        # These are dimensions in the game's native 320x240 UI
        # coordinate system, BEFORE game.scale is applied.
        #
        # The menu dimensions were calibrated against DELTARUNE.
        self.calibrated_sizes = {
            "menu_box": (68.5, 71.5),
        }

        # Scaled PhotoImage cache
        self.photo_cache = {}

    def get(self, name):
        """Return a PhotoImage scaled to the game's current scale."""

        scale = self.game.scale

        # Round the scale so tiny floating-point changes don't
        # constantly create new cached images.
        scale_key = round(scale, 3)

        cache_key = (name, scale_key)

        if cache_key in self.photo_cache:
            return self.photo_cache[cache_key]

        image = self.sprites[name]

        # --------------------------------
        # Apply UI calibration
        # --------------------------------
        print("before", image.size)
        if name in self.calibrated_sizes:
            calibrated_width, calibrated_height = self.calibrated_sizes[name]

            image = image.resize(
                (
                    max(1, round(calibrated_width* scale)),
                    max(1, round(calibrated_height* scale))
                ),
                Image.Resampling.NEAREST
            )
        print("after calibrated", image.size)
        # --------------------------------
        # Apply fullscreen/game scaling
        # --------------------------------

        if scale != 1:
            width = round(image.width * scale)
            height = round(image.height * scale)

            image = image.resize(
                (width, height),
                Image.Resampling.NEAREST
            )

        photo = ImageTk.PhotoImage(image)

        self.photo_cache[cache_key] = photo

        return photo

    def clear_cache(self):
        """Clear scaled sprites. Call this after a resize."""
        self.photo_cache.clear()