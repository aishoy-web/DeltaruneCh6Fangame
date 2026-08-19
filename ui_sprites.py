# Responsible for extracting the spritesheet assets
# and rendering the Deltarune small bitmap font.

from pathlib import Path
from PIL import Image, ImageTk


BASE_DIR = Path(__file__).resolve().parent

SPRITESHEET_PATH = (
    BASE_DIR / "sprites" / "ui" / "menu+HUD_spritesheet.png"
)

SMALL_FONT_PATH = (
    BASE_DIR / "sprites" / "ui" / "fnt_small.png"
)


class SmallFont:
    """
    Renderer for Deltarune's fnt_small bitmap font.

    The font atlas is a packed texture, so glyphs are
    extracted using their actual atlas coordinates rather
    than assuming a fixed grid.

    The atlas is rendered at native 320x240 UI resolution,
    then enlarged using the game's fullscreen scale.
    """

    GLYPHS = {
        # ------------------------------------------
        # Space
        # ------------------------------------------

        " ": {
            "x": 2,
            "y": 2,
            "w": 4,
            "h": 7,
            "offset": 0,
            "shift": 4,
        },

        # ------------------------------------------
        # Symbols
        # ------------------------------------------

        "$": {
            "x": 14,
            "y": 2,
            "w": 4,
            "h": 6,
            "offset": 0,
            "shift": 5,
        },

        "/": {
            "x": 92,
            "y": 18,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        # ------------------------------------------
        # Digits
        # ------------------------------------------

        "0": {
            "x": 8,
            "y": 18,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "1": {
            "x": 68,
            "y": 11,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "2": {
            "x": 74,
            "y": 18,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "3": {
            "x": 74,
            "y": 11,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "4": {
            "x": 44,
            "y": 11,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "5": {
            "x": 50,
            "y": 11,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "6": {
            "x": 92,
            "y": 11,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "7": {
            "x": 32,
            "y": 11,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "8": {
            "x": 80,
            "y": 18,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "9": {
            "x": 26,
            "y": 18,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        # ------------------------------------------
        # Uppercase letters needed by the HUD
        # ------------------------------------------

        "H": {
            "x": 116,
            "y": 18,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "K": {
            "x": 26,
            "y": 2,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "L": {
            "x": 14,
            "y": 11,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "P": {
            "x": 14,
            "y": 18,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },

        "V": {
            "x": 2,
            "y": 25,
            "w": 4,
            "h": 5,
            "offset": 0,
            "shift": 5,
        },
    }

    def __init__(self, game):
        self.game = game

        self.sheet = Image.open(
            SMALL_FONT_PATH
        ).convert("RGBA")

        # Cache:
        #
        # (text, scale) -> PhotoImage
        #
        self.cache = {}

    def render(self, text):
        """
        Render a string using fnt_small.

        The font is rendered at native UI resolution,
        then scaled with the game's current scale.
        """

        text = str(text)

        scale = float(self.game.scale)
        scale_key = round(scale, 4)

        cache_key = (
            text,
            scale_key
        )

        if cache_key in self.cache:
            return self.cache[cache_key]

        # ------------------------------------------
        # Calculate native dimensions
        # ------------------------------------------

        glyphs = []

        total_width = 0
        max_height = 1

        for char in text:

            # Unsupported characters are ignored.
            if char not in self.GLYPHS:
                continue

            glyph = self.GLYPHS[char]

            glyphs.append(
                (char, glyph)
            )

            total_width += glyph["shift"]

            max_height = max(
                max_height,
                glyph["h"] + glyph["offset"]
            )

        total_width = max(
            1,
            total_width
        )

        # ------------------------------------------
        # Create native-resolution text image
        # ------------------------------------------

        image = Image.new(
            "RGBA",
            (
                total_width,
                max_height
            ),
            (0, 0, 0, 0)
        )

        cursor_x = 0

        for char, glyph in glyphs:

            glyph_image = self.sheet.crop(
                (
                    glyph["x"],
                    glyph["y"],
                    glyph["x"] + glyph["w"],
                    glyph["y"] + glyph["h"]
                )
            )

            image.alpha_composite(
                glyph_image,
                (
                    cursor_x,
                    glyph["offset"]
                )
            )

            cursor_x += glyph["shift"]

        # ------------------------------------------
        # Fullscreen scaling
        # ------------------------------------------

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

        photo = ImageTk.PhotoImage(
            image
        )

        self.cache[cache_key] = photo

        return photo

    def clear_cache(self):
        self.cache.clear()


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
        # --------------------------------------------------

        self.calibrated_sizes = {
            "menu_box": (71, 74),
        }

        # --------------------------------------------------
        # Sprite cache
        # --------------------------------------------------

        self.photo_cache = {}

        # --------------------------------------------------
        # Small bitmap font
        # --------------------------------------------------

        self.small_font = SmallFont(game)

    def get(self, name):
        """
        Return a PhotoImage scaled to the game's
        current fullscreen scale.
        """

        scale = float(self.game.scale)

        scale_key = round(
            scale,
            4
        )

        cache_key = (
            name,
            scale_key
        )

        if cache_key in self.photo_cache:
            return self.photo_cache[cache_key]

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

        photo = ImageTk.PhotoImage(
            image
        )

        self.photo_cache[cache_key] = photo

        return photo

    def clear_cache(self):
        """Clear all cached scaled sprites."""

        self.photo_cache.clear()

        self.small_font.clear_cache()