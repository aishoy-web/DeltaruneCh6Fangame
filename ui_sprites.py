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

MAIN_FONT_PATH = (
    BASE_DIR / "sprites" / "ui" / "fnt_main.png"
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

        #open fonts
        self.smFont = Image.open(
            SMALL_FONT_PATH
        ).convert("RGBA")

        self.mnFont = Image.open(
            MAIN_FONT_PATH
        ).convert("RGBA")

        # Cache:
        #
        # (text, scale) -> PhotoImage
        #
        self.cache = {}

    def render(self, text):
        """
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

            glyph_image = self.smFont.crop(
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


class MainFont:
    """
    Renderer for Deltarune's fnt_main bitmap font.

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
            "x": 79,
            "y": 81,
            "w": 3,
            "h": 16,
            "offset": 0,
            "shift": 3,
        },

        # ------------------------------------------
        # Symbols
        # ------------------------------------------

        "!": {
            "x": 14,
            "y": 85,
            "w": 4,
            "h": 13,
            "offset": 1,
            "shift": 6,
        },

        "\"": {
            "x": 92,
            "y": 81,
            "w": 4,
            "h": 13,
            "offset": 0,
            "shift": 6,
        },

        "#": {
            "x": 92,
            "y": 81,
            "w": 5,
            "h": 8,
            "offset": 0,
            "shift": 8,
        },

        "$": {
            "x": 105,
            "y": 2,
            "w": 6,
            "h": 15,
            "offset": 0,
            "shift": 7,
        },

        "%": {
            "x": 51,
            "y": 2,
            "w": 7,
            "h": 13,
            "offset": 0,
            "shift": 8,
        },

        "&": {
            "x": 78,
            "y": 2,
            "w": 7,
            "h": 13,
            "offset": 0,
            "shift": 8,
        },

        "'": {
            "x": 119,
            "y": 81,
            "w": 2,
            "h": 8,
            "offset": 0,
            "shift": 3,
        },

        "(": {
            "x": 67,
            "y": 81,
            "w": 4,
            "h": 13,
            "offset": 0,
            "shift": 5,
        },

        ")": {
            "x": 55,
            "y": 81,
            "w": 4,
            "h": 13,
            "offset": 0,
            "shift": 5,
        },

        "*": {
            "x": 2,
            "y": 20,
            "w": 8,
            "h": 11,
            "offset": 0,
            "shift": 9,
        },

        "+": {
            "x": 98,
            "y": 66,
            "w": 6,
            "h": 11,
            "offset": 0,
            "shift": 7,
        },

        ",": {
            "x": 103,
            "y": 81,
            "w": 2,
            "h": 15,
            "offset": 0,
            "shift": 3,
        },

        "-": {
            "x": 41,
            "y": 81,
            "w": 6,
            "h": 9,
            "offset": 0,
            "shift": 7,
        },

        ".": {
            "x": 111,
            "y": 81,
            "w": 2,
            "h": 13,
            "offset": 0,
            "shift": 3,
        },

        "/": {
            "x": 20,
            "y": 20,
            "w": 6,
            "h": 14,
            "offset": 0,
            "shift": 7,
        },

        ":": {
            "x": 107,
            "y": 81,
            "w": 2,
            "h": 13,
            "offset": 0,
            "shift": 3,
        },

        ";": {
            "x": 99,
            "y": 81,
            "w": 2,
            "h": 15,
            "offset": 0,
            "shift": 3,
        },

        "<": {
            "x": 2,
            "y": 81,
            "w": 5,
            "h": 15,
            "offset": 0,
            "shift": 6,
        },

        "=": {
            "x": 33,
            "y": 81,
            "w": 6,
            "h": 10,
            "offset": 0,
            "shift": 7,
        },

        ">": {
            "x": 106,
            "y": 66,
            "w": 5,
            "h": 13,
            "offset": 0,
            "shift": 6,
        },

        "?": {
            "x": 114,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        "@": {
            "x": 106,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        "[": {
            "x": 61,
            "y": 81,
            "w": 4,
            "h": 13,
            "offset": 0,
            "shift": 5,
        },

        "\\": {
            "x": 12,
            "y": 20,
            "w": 6,
            "h": 14,
            "offset": 0,
            "shift": 7,
        },

        "]": {
            "x": 49,
            "y": 81,
            "w": 4,
            "h": 13,
            "offset": 0,
            "shift": 5,
        },

        "^": {
            "x": 84,
            "y": 81,
            "w": 6,
            "h": 7,
            "offset": 0,
            "shift": 7,
        },

        "_": {
            "x": 9,
            "y": 81,
            "w": 4,
            "h": 16,
            "offset": 0,
            "shift": 5,
        },

        "`": {
            "x": 2,
            "y": 99,
            "w": 3,
            "h": 5,
            "offset": 0,
            "shift": 4,
        },

        "{": {
            "x": 120,
            "y": 66,
            "w": 5,
            "h": 13,
            "offset": 0,
            "shift": 6,
        },

        "|": {
            "x": 115,
            "y": 81,
            "w": 2,
            "h": 13,
            "offset": 0,
            "shift": 3,
        },

        "}": {
            "x": 113,
            "y": 66,
            "w": 5,
            "h": 13,
            "offset": 0,
            "shift": 6,
        },

        "~": {
            "x": 24,
            "y": 81,
            "w": 7,
            "h": 9,
            "offset": 0,
            "shift": 8,
        },

        # ------------------------------------------
        # Digits
        # ------------------------------------------

        "0": {
            "x": 106,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "1": {
            "x": 74,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "2": {
            "x": 58,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "3": {
            "x": 108,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "4": {
            "x": 76,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "5": {
            "x": 66,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "6": {
            "x": 116,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "7": {
            "x": 26,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "8": {
            "x": 66,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        "9": {
            "x": 26,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        # ------------------------------------------
        # UPPERCASE LETTERS
        # ------------------------------------------

        "A": {
            "x": 2,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "B": {
            "x": 92,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "C": {
            "x": 34,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "D": {
            "x": 2,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "E": {
            "x": 34,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "F": {
            "x": 26,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "G": {
            "x": 100,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "H": {
            "x": 2,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "I": {
            "x": 36,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "J": {
            "x": 82,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        "K": {
            "x": 98,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        "L": {
            "x": 50,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "M": {
            "x": 87,
            "y": 2,
            "w": 7,
            "h": 13,
            "offset": 0,
            "shift": 8,
        },
        
        "N": {
            "x": 60,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "O": {
            "x": 18,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        "P": {
            "x": 34,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "Q": {
            "x": 113,
            "y": 2,
            "w": 6,
            "h": 15,
            "offset": 0,
            "shift": 7,
        },
        
        "R": {
            "x": 114,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "S": {
            "x": 42,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "T": {
            "x": 90,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "U": {
            "x": 42,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        "V": {
            "x": 10,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "W": {
            "x": 42,
            "y": 2,
            "w": 7,
            "h": 13,
            "offset": 0,
            "shift": 8,
        },
        
        "X": {
            "x": 28,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "Y": {
            "x": 18,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "Z": {
            "x": 90,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        # ------------------------------------------
        # lowercase letters 
        # ------------------------------------------
        
        "a": {
            "x": 10,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "b": {
            "x": 98,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },

        "c": {
            "x": 68,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "d": {
            "x": 66,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "e": {
            "x": 42,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "f": {
            "x": 50,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "g": {
            "x": 2,
            "y": 2,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "h": {
            "x": 52,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "i": {
            "x": 74,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "j": {
            "x": 18,
            "y": 2,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "k": {
            "x": 82,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "l": {
            "x": 50,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "m": {
            "x": 69,
            "y": 2,
            "w": 7,
            "h": 13,
            "offset": 0,
            "shift": 8,
        },
        
        "n": {
            "x": 10,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "o": {
            "x": 44,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "p": {
            "x": 34,
            "y": 2,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "q": {
            "x": 26,
            "y": 2,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "r": {
            "x": 74,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "s": {
            "x": 90,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "t": {
            "x": 18,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "u": {
            "x": 58,
            "y": 66,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "v": {
            "x": 58,
            "y": 36,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "w": {
            "x": 96,
            "y": 2,
            "w": 7,
            "h": 13,
            "offset": 0,
            "shift": 8,
        },
        
        "x": {
            "x": 84,
            "y": 20,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
        
        "y": {
            "x": 10,
            "y": 2,
            "w": 6,
            "h": 16,
            "offset": 0,
            "shift": 7,
        },
        
        "z": {
            "x": 82,
            "y": 51,
            "w": 6,
            "h": 13,
            "offset": 0,
            "shift": 7,
        },
    }

    def __init__(self, game):
        self.game = game

        #open fonts
        self.mnFont = Image.open(
            MAIN_FONT_PATH
        ).convert("RGBA")

        # Cache:
        #
        # (text, scale) -> PhotoImage
        #
        self.cache = {}

    def render(self, text, color = "white"):
        """
        The font is rendered at native UI resolution,
        then scaled with the game's current scale.
        """

        text = str(text)

        scale = float(self.game.scale)
        scale_key = round(scale, 4)

        cache_key = (
            text,
            scale_key,
            color
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

            glyph_image = self.mnFont.crop(
                (
                    glyph["x"],
                    glyph["y"],
                    glyph["x"] + glyph["w"],
                    glyph["y"] + glyph["h"]
                )
            )

            colored_glyph = Image.new(
                "RGBA",
                glyph_image.size,
                color
            )

            colored_glyph.putalpha(
                glyph_image.getchannel("A")
            )

            glyph_image = colored_glyph

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

            "menu_box_item": self.sheet.crop(
                (370, 119, 543, 300)
            ),
            "menu_box_stat": self.sheet.crop(
                (370, 304, 543, 513)
            )
        }

        # --------------------------------------------------
        # Calibrated native UI dimensions
        # --------------------------------------------------

        self.calibrated_sizes = {
            "menu_box": (71, 74),
            "menu_box_item": (173, 181),
            "menu_box_stat": (173, 209)
        }

        # --------------------------------------------------
        # Sprite cache
        # --------------------------------------------------

        self.photo_cache = {}

        # --------------------------------------------------
        # Small bitmap font
        # --------------------------------------------------

        self.small_font = SmallFont(game)
        self.main_font = MainFont(game)

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