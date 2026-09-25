from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

try:
    import pygame
except Exception:  # pragma: no cover - project normally has pygame
    pygame = None


BASE_DIR = Path(__file__).resolve().parent
SFX_DIR = BASE_DIR / "sfx"


# ============================================================
# Dialogue data
# ============================================================


@dataclass
class Dialogue:
    """One logical dialogue entry.

    ``voice`` is retained for compatibility with the project's existing
    room dialogue definitions.  New dialogue should normally prefer
    ``typer`` so the writer can select the complete DELTARUNE text profile
    (font, color, rate, spacing, and text sound) in one place.
    """

    voice: object | None = None
    text_id: str = ""
    choices: list | None = None
    scene_id: str | None = None
    sound_effect: object | None = None
    typer: int | None = None
    skippable: bool = True


@dataclass(frozen=True)
class WriterProfile:
    """Python equivalent of one ``scr_texttype`` / ``scr_textsetup`` preset."""

    font: str = "main"
    color: str = "#ffffff"
    charline: int = 33
    shake: int = 0
    rate: int = 1
    sound: str | None = "snd_text"
    hspace: int = 8
    vspace: int = 18
    special: int = 0
    textscale: float = 1.0


def _profile(
    font="main",
    color="#ffffff",
    charline=33,
    shake=0,
    rate=1,
    sound="snd_text",
    hspace=8,
    vspace=18,
    special=0,
    textscale=1.0,
):
    if sound == "snd_nosound":
        sound = None

    return WriterProfile(
        font=font,
        color=color,
        charline=charline,
        shake=shake,
        rate=rate,
        sound=sound,
        hspace=hspace,
        vspace=vspace,
        special=special,
        textscale=textscale,
    )


# A direct, compact translation of the useful ``scr_texttype`` profiles.
# Profiles that only differ in Chapter-5-specific effects still live here so
# the parser can switch to them without needing another architecture change.
WRITER_PROFILES: dict[int, WriterProfile] = {
    1: _profile(),
    2: _profile(rate=2, sound=None),
    3: _profile(rate=2, special=1),
    4: _profile(font="mainbig", rate=1, hspace=16, vspace=28, special=1),
    5: _profile(),
    6: _profile(font="mainbig", hspace=16, vspace=36, special=1),
    7: _profile(sound="snd_txttor"),
    8: _profile(rate=2, sound="snd_txttor"),
    10: _profile(sound="snd_txtsus"),
    11: _profile(sound="snd_txtsus"),
    12: _profile(sound="snd_txtnoe"),
    13: _profile(sound="snd_txtber"),
    14: _profile(font="comicsans", sound="snd_txtsans"),
    15: _profile(),
    17: _profile(sound="snd_txtund"),
    18: _profile(sound="snd_txtasg"),
    19: _profile(),
    20: _profile(sound="snd_txtal"),
    21: _profile(sound="snd_txtal"),
    22: _profile(font="tinynoelle", sound="snd_txtal", hspace=6),
    23: _profile(font="tinynoelle", sound="snd_txtnoe", hspace=6),
    30: _profile(font="mainbig", sound="snd_txtsus", hspace=16, vspace=36, special=1),
    31: _profile(font="mainbig", sound="snd_txtral", hspace=16, vspace=36, special=1),
    32: _profile(font="mainbig", sound="snd_txtlan", hspace=16, vspace=36, special=1),
    33: _profile(font="mainbig", sound="snd_dadtxt", hspace=16, vspace=36, special=1),
    35: _profile(font="mainbig", sound="snd_txtjok", hspace=16, vspace=36, special=1),
    36: _profile(font="mainbig", sound=None, hspace=16, vspace=36, special=1),
    37: _profile(font="mainbig", rate=3, sound="snd_txtsus", hspace=18, vspace=36, special=1),
    40: _profile(rate=2, sound=None),
    41: _profile(rate=3, sound=None),
    42: _profile(font="mainbig", rate=2, sound=None, hspace=16, vspace=36, special=1),
    45: _profile(font="mainbig", sound="snd_txtral", hspace=16, vspace=28, special=1),
    46: _profile(font="mainbig", sound="snd_txtlan", hspace=16, vspace=28, special=1),
    47: _profile(font="mainbig", sound="snd_txtsus", hspace=16, vspace=28, special=1),
    48: _profile(font="mainbig", sound="snd_dadtxt", hspace=16, vspace=28, special=1),
    50: _profile(font="dotumche", color="#000000", hspace=9, vspace=20),
    51: _profile(font="mainbig", rate=10, hspace=16, vspace=36, special=1),
    52: _profile(font="mainbig", rate=6, hspace=16, vspace=36, special=1),
    53: _profile(font="dotumche", color="#000000", sound="snd_txtsus", hspace=9, vspace=20),
    54: _profile(font="dotumche", color="#000000", rate=2, sound="snd_txtsus", hspace=9, vspace=20),
    55: _profile(sound="snd_txtrud"),
    56: _profile(font="mainbig", sound="snd_txtnoe", hspace=16, vspace=36, special=1),
    57: _profile(font="mainbig", sound="snd_txtber", hspace=16, vspace=36, special=1),
    58: _profile(font="mainbig", sound="snd_txtq", hspace=16, vspace=36, special=1),
    59: _profile(font="mainbig", sound="snd_txtnoe", hspace=16, vspace=28, special=1),
    60: _profile(rate=2, sound="snd_txtral", hspace=12, vspace=20),
    61: _profile(rate=2, sound="snd_txtsus", hspace=12, vspace=20),
    62: _profile(font="mainbig", sound="snd_txtq_2", hspace=16, vspace=36, special=1),
    63: _profile(rate=2, sound="snd_txtnoe"),
    64: _profile(shake=1, rate=2, sound="snd_txtnoe"),
    65: _profile(font="mainbig", sound="snd_txtrx1", hspace=16, vspace=36, special=1),
    66: _profile(font="mainbig", sound="snd_txtspam", hspace=16, vspace=36, special=1),
    67: _profile(font="mainbig", sound="snd_txtspam2", hspace=16, vspace=36, special=1),
    68: _profile(font="dotumche", color="#000000", sound="snd_txtspam", hspace=9, vspace=20),
    69: _profile(font="dotumche", color="#000000", sound="snd_txtber", hspace=9, vspace=20),
    70: _profile(font="dotumche", color="#000000", sound="snd_txtq", hspace=9, vspace=20),
    71: _profile(font="dotumche", color="#000000", sound="snd_txtq", hspace=9, vspace=20),
    72: _profile(font="dotumche", color="#000000", sound="snd_txtspam2", hspace=9, vspace=20),
    74: _profile(font="dotumche", color="#000000", sound="snd_txtral", hspace=9, vspace=20),
    75: _profile(font="dotumche", color="#000000", sound="snd_txtsus", hspace=9, vspace=20),
    76: _profile(font="dotumche", color="#000000", sound="snd_txtnoe", hspace=9, vspace=20),
    77: _profile(font="mainbig", sound="snd_txtber", hspace=16, vspace=28, special=1),
    78: _profile(font="mainbig", charline=36, hspace=16, vspace=36, special=1),
    79: _profile(font="mainbig", sound="snd_txtsusral", hspace=16, vspace=36, special=1),
    83: _profile(font="mainbig", sound="snd_txtjack_low2", hspace=16, vspace=36, special=1),
    84: _profile(font="mainbig", sound="snd_tv_voice_short", hspace=16, vspace=36, special=1),
    86: _profile(font="mainbig", sound="snd_flowery_voicenoise_loop", hspace=16, vspace=36, special=1),
    87: _profile(sound="snd_txtcar"),
    88: _profile(font="mainbig", sound="snd_flowery_voicenoise_1", hspace=16, vspace=36, special=1),
    89: _profile(font="mainbig", sound="snd_txtasg", hspace=16, vspace=36, special=1),
    90: _profile(font="mainbig", color="#84F9FF", hspace=16, vspace=36, special=1),
    91: _profile(font="mainbig", color="#E2A8FC", hspace=16, vspace=36, special=1),
    92: _profile(font="mainbig", color="#FFF8A1", hspace=16, vspace=36, special=1),
    93: _profile(font="mainbig", color="#FFAC87", hspace=16, vspace=36, special=1),
    94: _profile(font="mainbig", color="#86A7FF", hspace=16, vspace=36, special=1),
    95: _profile(font="mainbig", color="#AEFFBC", hspace=16, vspace=36, special=1),
    96: _profile(font="dotumche", color="#000000", sound="snd_flowery_voicenoise_1", hspace=9, vspace=20),
    97: _profile(font="mainbig", hspace=16, vspace=36, special=1),
    98: _profile(font="mainbig", color="#ffa500", shake=1, hspace=16, vspace=36),
    99: _profile(font="mainbig", rate=2, sound="snd_txtsus", hspace=18, vspace=36, special=1),
    100: _profile(font="8bit", charline=22, hspace=16, vspace=20),
    200: _profile(font="dotumche", color="#000000", sound="snd_txtsus", hspace=9, vspace=20),
    201: _profile(font="dotumche", color="#000000", sound="snd_txtral", hspace=9, vspace=20),
    202: _profile(font="mainbig", rate=2, sound="snd_txtral", hspace=16, vspace=36, special=1),
    203: _profile(font="mainbig", rate=4, hspace=16, vspace=36, special=1),
    666: _profile(rate=4, sound=None, hspace=12, vspace=20, special=2),
    667: _profile(rate=2, sound=None, hspace=12, vspace=20, special=2),
    999: _profile(rate=4, sound="snd_txtecho", special=3),
}


DEFAULT_WRITER_PROFILE = WRITER_PROFILES[1]


# ============================================================
# Parsed writer data
# ============================================================


@dataclass
class WriterToken:
    kind: str
    value: object = None


@dataclass
class VisibleGlyph:
    """One character position produced by the writer.

    ``char`` is ``None`` for DELTARUNE's ``|`` spacing control.  The box still
    advances by hspace, but no glyph is drawn.
    """

    char: str | None
    color: str = "#ffffff"
    shake: int = 0
    rainbow: bool = False


PAUSE_FRAMES = {
    "1": 5,
    "2": 10,
    "3": 15,
    "4": 20,
    "5": 30,
    "6": 40,
    "7": 60,
    "8": 90,
    "9": 150,
}


COLOR_CODES = {
    "R": "#ff0000",
    "B": "#0000ff",
    "Y": "#ffff00",
    "G": "#00ff00",
    "W": "#ffffff",
    "X": "#000000",
    "P": "#800080",
    "M": "#800000",
    "S": "#ff80ff",
    "V": "#80ff80",
    "a": "#84F9FF",
    "y": "#FFF8A1",
    "g": "#AEFFBC",
    "o": "#FFAC87",
    "s": "#E2A8FC",
    "p": "#FF8A90",
    "b": "#86A7FF",
}


# Light-World/default results for the \T commands from obj_writer Draw.
TYPE_COMMANDS = {
    "0": 5,
    "1": 2,
    "A": 18,
    "a": 20,
    "N": 12,
    "n": 23,
    "B": 13,
    "S": 10,
    "R": 31,
    "L": 32,
    "X": 40,
    "r": 55,
    "T": 7,
    "J": 35,
    "K": 33,
    "q": 62,
    "Q": 58,
    "s": 14,
    "U": 17,
    "p": 67,
    "C": 87,
    "f": 83,
    "v": 84,
    "j": 5,
    "y": 5,
    "i": 5,
    "k": 5,
    "F": 88,
    "h": 86,
    "+": 36,
    "4": 90,
    "5": 91,
    "6": 92,
    "7": 93,
    "8": 94,
    "9": 95,
    "P": 97,
    "O": 98,
}

# ============================================================
# Dialogue authoring language
# ============================================================


class DialoguePart:
    def compile(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class Text(DialoguePart):
    value: str

    def compile(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Pause(DialoguePart):
    frames: int

    def compile(self) -> str:
        frames = max(0, int(self.frames))
        nearest = min(PAUSE_FRAMES, key=lambda key: abs(PAUSE_FRAMES[key] - frames))
        return "^" + nearest


@dataclass(frozen=True)
class Face(DialoguePart):
    character: str | None
    expression: int | str | None = None

    FACE_TO_CODE = {
        None: "0", "susie": "S", "ralsei": "R", "noelle": "N",
        "toriel": "T", "lancer": "L", "sans": "s", "undyne": "U",
        "asgore": "A", "alphys": "a", "berdly": "B", "rudy": "r",
        "catty": "u", "king": "K", "queen": "Q", "jevil": "J",
    }

    @staticmethod
    def _expression_code(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str) and len(value) == 1:
            return value
        number = max(0, int(value))
        if number <= 9:
            return str(number)
        if number <= 35:
            return chr(number + 55)
        return chr(min(number, 61) + 61)

    def compile(self) -> str:
        code = self.FACE_TO_CODE.get(self.character, str(self.character or "0")[:1])
        result = "\\F" + code
        expression = self._expression_code(self.expression)
        if expression:
            result += "\\E" + expression
        return result


@dataclass(frozen=True)
class Expression(DialoguePart):
    value: int | str

    def compile(self) -> str:
        return "\\E" + Face._expression_code(self.value)


@dataclass(frozen=True)
class TextType(DialoguePart):
    value: int | str

    TYPE_TO_CODE = {
        "susie": "S", "ralsei": "R", "noelle": "N", "berdly": "B",
        "toriel": "T", "sans": "s", "undyne": "U", "asgore": "A",
        "alphys": "a", "queen": "Q",
    }

    def compile(self) -> str:
        if isinstance(self.value, str) and self.value in self.TYPE_TO_CODE:
            return "\\T" + self.TYPE_TO_CODE[self.value]
        if isinstance(self.value, str) and len(self.value) == 1:
            return "\\T" + self.value
        target = int(self.value)
        for code, typer in TYPE_COMMANDS.items():
            if typer == target:
                return "\\T" + code
        return ""


@dataclass(frozen=True)
class Color(DialoguePart):
    code: str

    def compile(self) -> str:
        return "\\c" + str(self.code)[:1]


@dataclass(frozen=True)
class Skippable(DialoguePart):
    enabled: bool

    def compile(self) -> str:
        return "\\s1" if self.enabled else "\\s0"


@dataclass(frozen=True)
class Wait(DialoguePart):
    final: bool = False

    def compile(self) -> str:
        return "/%" if self.final else "/"


@dataclass(frozen=True)
class NewLine(DialoguePart):
    def compile(self) -> str:
        return "&"


@dataclass
class Message:
    parts: Sequence[DialoguePart | str]
    typer: int | None = None
    choices: list | None = None
    sound_effect: object | None = None
    skippable: bool = True

    def __init__(self, *parts, typer=None, choices=None, sound_effect=None, skippable=True):
        self.parts = parts
        self.typer = typer
        self.choices = choices
        self.sound_effect = sound_effect
        self.skippable = skippable

    def compile(self) -> str:
        return "".join(
            part.compile() if isinstance(part, DialoguePart) else str(part)
            for part in self.parts
        )

    def to_dialogue(self) -> Dialogue:
        return Dialogue(
            text_id=self.compile(),
            choices=self.choices,
            sound_effect=self.sound_effect,
            typer=self.typer,
            skippable=self.skippable,
        )


@dataclass
class DialogueScript:
    id: str
    messages: Sequence[Message | Dialogue | str]

    def entries(self) -> list[Dialogue | str]:
        result = []
        for message in self.messages:
            if isinstance(message, Message):
                result.append(message.to_dialogue())
            else:
                result.append(message)
        return result




__all__ = [
    "Dialogue",
    "WriterProfile",
    "WriterToken",
    "VisibleGlyph",
    "WRITER_PROFILES",
    "DEFAULT_WRITER_PROFILE",
    "DialogueScript",
    "Message",
    "DialoguePart",
    "Text",
    "Pause",
    "Face",
    "Expression",
    "TextType",
    "Color",
    "Skippable",
    "Wait",
    "NewLine",
]
