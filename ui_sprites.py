# Responsible for extracting the spritesheet assets

from pathlib import Path
from PIL import Image, ImageTk


BASE_DIR = Path(__file__).resolve().parent
SPRITESHEET_PATH = (
    BASE_DIR / "sprites" / "ui" / "menu+HUD_spritesheet.png"
)


class UISpriteSheet:
    def __init__(self, game):
        self.game = game

        self.sheet = Image.open(
            SPRITESHEET_PATH
        ).convert("RGBA")

        # --------------------------------------------------
        # Native-resolution sprites
        # --------------------------------------------------

        self.sprites = {
            "dialogue_box": self.sheet.crop(
                (292, 19, 581, 95)
            ),

            "status_box": self.sheet.crop(
                (292, 119, 363, 174)
            ),

            "menu_box": self.sheet.crop(
                (292, 177, 363, 251)
            ),
        }

        # --------------------------------------------------
        # Calibrated native UI dimensions
        #
        # These are dimensions in the game's 320x240
        # coordinate system BEFORE fullscreen scaling.
        # --------------------------------------------------

        self.calibrated_sizes = {
            "menu_box": (71, 74), 
        }

        # Cache:
        # (sprite name, scale) -> PhotoImage
        self.photo_cache = {}

    def get(self, name):
        """
        Return a PhotoImage scaled to the game's
        current fullscreen scale.
        """

        scale = float(self.game.scale)

        # Avoid creating duplicate cache entries from
        # tiny floating-point differences.
        scale_key = round(scale, 4)

        cache_key = (name, scale_key)

        if cache_key in self.photo_cache:
            return self.photo_cache[cache_key]

        # Start with the native sprite.
        image = self.sprites[name]

        # --------------------------------------------------
        # Apply native-size calibration
        # --------------------------------------------------

        if name in self.calibrated_sizes:
            native_width, native_height = (
                self.calibrated_sizes[name]
            )

            image = image.resize(
                (
                    round(native_width),
                    round(native_height)
                ),
                Image.Resampling.NEAREST
            )

        # --------------------------------------------------
        # Apply fullscreen scaling
        # --------------------------------------------------

        scaled_width = max(
            1,
            round(image.width * scale)
        )

        scaled_height = max(
            1,
            round(image.height * scale)
        )

        image = image.resize(
            (
                scaled_width,
                scaled_height
            ),
            Image.Resampling.NEAREST
        )

        photo = ImageTk.PhotoImage(image)

        self.photo_cache[cache_key] = photo

        return photo

    def clear_cache(self):
        """Clear all cached scaled sprites."""
        self.photo_cache.clear()