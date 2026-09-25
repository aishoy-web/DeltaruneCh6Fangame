from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PortraitDefinition:
    """Definition for one dialogue portrait family.

    ``loader`` receives the current expression number and should return either a
    PIL image, a filesystem path, or ``None``.  ``mouth_loader`` is optional;
    when omitted, mouth animation still runs internally but the same image is
    used for open/closed states.
    """

    loader: Callable[[int], object | None]
    mouth_loader: Callable[[int, bool], object | None] | None = None
    offset_x: int = 0
    offset_y: int = 0
    width: int = 58


class DialoguePortrait:
    """Python counterpart to obj_face / obj_face_parent.

    The writer owns *when* the portrait changes and *when* a speaking pulse is
    triggered.  This object owns portrait lookup and the short mouth animation
    used by DELTARUNE's face objects.
    """

    FACE_CODES = {
        "0": None,
        "S": "susie",
        "R": "ralsei",
        "N": "noelle",
        "T": "toriel",
        "L": "lancer",
        "s": "sans",
        "U": "undyne",
        "A": "asgore",
        "a": "alphys",
        "B": "berdly",
        "i": "catti",
        "r": "rudy",
        "u": "catty",
        "K": "king",
        "Q": "queen",
        "C": "carol",
        "F": "flowey",
        "f": "flowey_alt",
        "J": "jevil",
        "y": "tenna",
        "k": "knight",
    }

    DEFAULT_OFFSETS = {
        "susie": (-5, 0),
        "ralsei": (-15, -10),
        "noelle": (-12, -10),
        "toriel": (0, 0),
        "lancer": (-15, -10),
        "sans": (0, 0),
        "undyne": (-10, 0),
        "asgore": (-10, 0),
        "alphys": (-10, 0),
        "berdly": (-10, 0),
        "catti": (-10, 0),
        "rudy": (-12, -10),
        "catty": (-10, 0),
    }

    def __init__(self, game, box=None):
        self.game = game
        self.box = box

        self.registry: dict[str, PortraitDefinition] = {}

        self.face_code: str | None = None
        self.character: str | None = None
        self.expression = 0

        self.buffer = 4
        self.mouthmove = False
        self.mouthtimer = 0
        self.mouth_rate = 1
        self.mouth_open = False

        self.image = None
        self.offset_x = 0
        self.offset_y = 0
        self.width = 58

    # --------------------------------------------------
    # Registry
    # --------------------------------------------------

    def register(self, name: str, definition: PortraitDefinition):
        self.registry[str(name)] = definition
        if self.character == name:
            self.refresh()

    def register_static(
        self,
        name: str,
        path: str | Path,
        *,
        offset_x: int | None = None,
        offset_y: int | None = None,
        width: int = 58,
    ):
        path = Path(path)
        if not path.is_absolute():
            path = BASE_DIR / path

        default = self.DEFAULT_OFFSETS.get(name, (0, 0))
        ox = default[0] if offset_x is None else int(offset_x)
        oy = default[1] if offset_y is None else int(offset_y)

        def loader(_expression):
            if not path.exists():
                return None
            return path

        self.register(
            name,
            PortraitDefinition(
                loader=loader,
                offset_x=ox,
                offset_y=oy,
                width=width,
            ),
        )

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    @staticmethod
    def decode_expression(code) -> int:
        text = str(code)
        if not text:
            return 0
        ch = text[0]
        if "0" <= ch <= "9":
            return int(ch)
        if "A" <= ch <= "Z":
            return ord(ch) - 55
        if "a" <= ch <= "z":
            return ord(ch) - 61
        return 0

    def set_face_code(self, code):
        self.face_code = None if code is None else str(code)
        self.character = self.FACE_CODES.get(self.face_code, self.face_code)
        self.buffer = 4
        self.mouthmove = False
        self.mouthtimer = 0
        self.mouth_open = False
        self.refresh()

    def set_expression_code(self, code):
        self.expression = self.decode_expression(code)
        self.refresh()

    def clear(self):
        self.face_code = None
        self.character = None
        self.expression = 0
        self.image = None
        self.mouthmove = False
        self.mouthtimer = 0
        self.mouth_open = False
        self._push_to_box()

    # --------------------------------------------------
    # Mouth animation
    # --------------------------------------------------

    def trigger_mouth(self):
        self.mouthmove = True

    def update(self):
        self.buffer -= 1

        if self.buffer < 0 and self.mouthmove and self.mouthtimer == 0:
            self.mouthtimer = 1

        if self.mouthtimer > 0:
            self.mouthtimer += self.mouth_rate

        new_open = 1 <= self.mouthtimer <= 5
        if new_open != self.mouth_open:
            self.mouth_open = new_open
            self.refresh()

        if self.mouthtimer >= 9:
            self.mouthtimer = 0
            self.mouthmove = False
            if self.mouth_open:
                self.mouth_open = False
                self.refresh()

    # --------------------------------------------------
    # Image resolution
    # --------------------------------------------------

    @staticmethod
    def _coerce_image(value):
        if value is None:
            return None
        if isinstance(value, Image.Image):
            return value.convert("RGBA")
        try:
            path = Path(value)
            if path.exists():
                return Image.open(path).convert("RGBA")
        except Exception:
            pass
        return None

    def refresh(self):
        if self.character is None:
            self.image = None
            self._push_to_box()
            return

        definition = self.registry.get(self.character)
        if definition is None:
            self.image = None
            self.offset_x, self.offset_y = self.DEFAULT_OFFSETS.get(
                self.character,
                (0, 0),
            )
            self.width = 58
            self._push_to_box()
            return

        if definition.mouth_loader is not None:
            value = definition.mouth_loader(self.expression, self.mouth_open)
        else:
            value = definition.loader(self.expression)

        self.image = self._coerce_image(value)
        self.offset_x = definition.offset_x
        self.offset_y = definition.offset_y
        self.width = definition.width
        self._push_to_box()

    def _push_to_box(self):
        if self.box is None:
            return
        method = getattr(self.box, "_apply_portrait_state", None)
        if callable(method):
            method(self)


__all__ = ["DialoguePortrait", "PortraitDefinition"]
