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


class DialogueWriter:
    """A frame-driven Python counterpart to ``obj_writer``.

    The writer deliberately does *not* own the dialogue box.  It produces
    visible glyphs and tells an attached ``DialogueBox`` what to render.  This
    lets room dialogue, ITEM/INFO/DROP text, and cutscenes all share the same
    writer without duplicating typewriter logic.

    Call ``update()`` once per logical game frame.  The default DELTARUNE
    profile has ``rate == 1``, so one writer step occurs per logical frame.
    """

    def __init__(self, game, box=None):
        self.game = game
        self.box = None

        self.active = False
        self.auto_close = True

        self.entries: list[Dialogue] = []
        self.messages: list[str] = []
        self.message_index = 0

        self.tokens: list[WriterToken] = []
        self.token_index = 0
        self.visible_glyphs: list[VisibleGlyph] = []

        self.typer = 1
        self.default_typer = 1
        self.profile = DEFAULT_WRITER_PROFILE
        self.base_profile = DEFAULT_WRITER_PROFILE

        self.rate = 1
        self.timer = 0.0
        self.sound_timer = 0

        self.reached_end = False
        self.halt = 0
        self.skippable = True
        self.prevent_char_skip = False

        self.current_color = "#ffffff"
        self.rainbow = False
        self.face_code = None
        self.expression_code = None
        self.choice_request = None

        self.current_entry: Dialogue | None = None
        self.current_voice_override = None

        self.on_complete: Callable[[], None] | None = None
        self.on_choices: Callable[[list], None] | None = None
        self.on_command: Callable[[str, str], None] | None = None

        self._sound_cache = {}

        if box is not None:
            self.attach_box(box)

    # --------------------------------------------------------
    # Setup / lifecycle
    # --------------------------------------------------------

    def attach_box(self, box):
        self.box = box
        if hasattr(box, "attach_writer"):
            box.attach_writer(self)

    def set_type(self, typer: int):
        self.typer = int(typer)
        self.profile = WRITER_PROFILES.get(
            self.typer,
            DEFAULT_WRITER_PROFILE,
        )

        self.rate = max(1, int(self.profile.rate))
        self.current_color = self.profile.color

        if self.box is not None:
            self.box.set_writer_metrics(
                hspace=self.profile.hspace,
                vspace=self.profile.vspace,
                font_name=self.profile.font,
                textscale=self.profile.textscale,
            )

    def start(
        self,
        dialogue: Dialogue | str | Sequence[Dialogue | str],
        *,
        text_lookup: dict | Callable[[str], str] | None = None,
        typer: int | None = None,
        on_complete: Callable[[], None] | None = None,
        on_choices: Callable[[list], None] | None = None,
        auto_close: bool = True,
        show_box: bool = True,
    ):
        if isinstance(dialogue, (Dialogue, str)):
            source = [dialogue]
        else:
            source = list(dialogue)

        self.entries = []
        self.messages = []

        for item in source:
            if isinstance(item, Dialogue):
                entry = item
                text = self._resolve_text(entry.text_id, text_lookup)
            else:
                entry = Dialogue(text_id=str(item))
                text = str(item)

            self.entries.append(entry)
            self.messages.append(text)

        self.message_index = 0
        self.on_complete = on_complete
        self.on_choices = on_choices
        self.auto_close = bool(auto_close)
        self.default_typer = (
            1
            if typer is None
            else int(typer)
        )
        self.active = bool(self.messages)

        if not self.active:
            self._finish_all()
            return

        if self.box is not None and show_box:
            self.box.show()
            self.box.update_position()

        self._load_message(0)

    def stop(self, hide_box: bool | None = None):
        self.active = False
        self.tokens = []
        self.visible_glyphs = []
        self.token_index = 0
        self.timer = 0
        self.reached_end = False
        self.halt = 0
        self.choice_request = None

        if self.box is not None:
            try:
                self.box.set_glyphs([])
            except Exception:
                pass

        if hide_box is None:
            hide_box = self.auto_close

        if hide_box and self.box is not None:
            self.box.hide()

    @staticmethod
    def _resolve_text(text_id, text_lookup):
        if text_lookup is None:
            return str(text_id)

        if callable(text_lookup):
            try:
                return str(text_lookup(text_id))
            except Exception:
                return str(text_id)

        try:
            return str(text_lookup.get(text_id, text_id))
        except Exception:
            return str(text_id)

    def _load_message(self, index: int):
        if not (0 <= index < len(self.messages)):
            self._finish_all()
            return

        self.message_index = index
        self.current_entry = self.entries[index]
        self.current_voice_override = self.current_entry.voice

        entry_typer = self.current_entry.typer
        self.set_type(
            self.default_typer
            if entry_typer is None
            else entry_typer
        )
        self.base_profile = self.profile

        self.skippable = bool(self.current_entry.skippable)
        self.current_color = self.profile.color
        self.rainbow = False
        self.face_code = None
        self.expression_code = None
        self.choice_request = None

        self.reached_end = False
        self.halt = 0
        self.sound_timer = 0
        self.timer = float(self.rate)
        self.token_index = 0
        self.visible_glyphs = []

        raw = self.messages[index]
        self.tokens = self._wrap_tokens(
            self._tokenize(raw),
            self.profile.charline,
        )

        if self.current_entry.sound_effect is not None:
            try:
                self.current_entry.sound_effect.play()
            except Exception:
                pass

        self._render()

    # --------------------------------------------------------
    # Tokenizing / formatting
    # --------------------------------------------------------

    def _tokenize(self, text: str) -> list[WriterToken]:
        tokens: list[WriterToken] = []
        i = 0

        while i < len(text):
            char = text[i]

            # Backtick escapes the next character from writer parsing.
            if char == "`" and i + 1 < len(text):
                tokens.append(WriterToken("char", text[i + 1]))
                i += 2
                continue

            if char in ("&", "\n"):
                tokens.append(WriterToken("newline"))
                i += 1
                continue

            if char == "|":
                tokens.append(WriterToken("spacer"))
                i += 1
                continue

            if char == "^" and i + 1 < len(text):
                delay_code = text[i + 1]
                tokens.append(
                    WriterToken(
                        "pause",
                        PAUSE_FRAMES.get(delay_code, 0),
                    )
                )
                i += 2
                continue

            if char == "/":
                final = i + 1 < len(text) and text[i + 1] == "%"
                tokens.append(WriterToken("halt", 2 if final else 1))
                i += 2 if final else 1
                continue

            if char == "\\" and i + 2 < len(text):
                tokens.append(
                    WriterToken(
                        "command",
                        (text[i + 1], text[i + 2]),
                    )
                )
                i += 3
                continue

            # A naked % is formatting metadata in obj_writer, not a glyph.
            if char == "%":
                i += 1
                continue

            tokens.append(WriterToken("char", char))
            i += 1

        return tokens

    @staticmethod
    def _visible_width(token: WriterToken) -> int:
        if token.kind in ("char", "spacer"):
            return 1
        return 0

    def _wrap_tokens(
        self,
        tokens: list[WriterToken],
        charline: int,
    ) -> list[WriterToken]:
        """Approximate obj_writer Other_15's word wrapping.

        DELTARUNE wraps at the most recent space when possible and inserts a
        writer newline.  Explicit newlines remain untouched.
        """

        if charline <= 0:
            return list(tokens)

        result: list[WriterToken] = []
        line_width = 0
        last_space_result_index: int | None = None

        for token in tokens:
            if token.kind == "newline":
                result.append(token)
                line_width = 0
                last_space_result_index = None
                continue

            result.append(token)

            if token.kind == "char" and token.value == " ":
                last_space_result_index = len(result) - 1

            line_width += self._visible_width(token)

            if line_width < charline:
                continue

            if last_space_result_index is not None:
                wrap_index = last_space_result_index
                result[wrap_index] = WriterToken("newline")

                line_width = sum(
                    self._visible_width(t)
                    for t in result[wrap_index + 1 :]
                    if t.kind != "newline"
                )

                # Only remember spaces that belong to the newly wrapped line.
                last_space_result_index = None
                for idx in range(wrap_index + 1, len(result)):
                    candidate = result[idx]
                    if candidate.kind == "newline":
                        last_space_result_index = None
                    elif (
                        candidate.kind == "char"
                        and candidate.value == " "
                    ):
                        last_space_result_index = idx
            else:
                # No usable space: break before the next printable token.
                result.append(WriterToken("newline"))
                line_width = 0
                last_space_result_index = None

        return result

    # --------------------------------------------------------
    # Frame update
    # --------------------------------------------------------

    def update(self, frames: float = 1.0):
        if not self.active or self.reached_end:
            return

        self.timer -= float(frames)

        # Alarm-style stepping.  A large dt may process more than one writer
        # alarm, but is capped so a stalled Tk frame cannot dump a whole page.
        safety = 0
        while self.timer <= 0 and self.active and not self.reached_end:
            safety += 1
            if safety > 8:
                self.timer = 1
                break

            self._writer_alarm()

    def _writer_alarm(self):
        if self.sound_timer > 0:
            self.sound_timer -= 1

        if self.token_index >= len(self.tokens):
            self.reached_end = True
            self._on_page_finished()
            return

        token = self.tokens[self.token_index]
        self.token_index += 1

        # Default next alarm is the current profile's rate.
        self.timer += max(1, self.rate)

        if token.kind == "char":
            char = str(token.value)
            self.visible_glyphs.append(
                VisibleGlyph(
                    char=char,
                    color=self.current_color,
                    shake=self.profile.shake,
                    rainbow=self.rainbow,
                )
            )
            self._maybe_text_sound(char)
            self._render()
            return

        if token.kind == "newline":
            self.visible_glyphs.append(
                VisibleGlyph(char="\n", color=self.current_color)
            )
            self._render()
            return

        if token.kind == "spacer":
            self.visible_glyphs.append(
                VisibleGlyph(char=None, color=self.current_color)
            )
            self._render()
            return

        if token.kind == "pause":
            self.timer += int(token.value or 0)
            return

        if token.kind == "halt":
            self.halt = int(token.value or 1)
            self.reached_end = True
            self._on_page_finished()
            return

        if token.kind == "command":
            command, argument = token.value
            self._handle_command(str(command), str(argument))
            return

    # --------------------------------------------------------
    # Input / page control
    # --------------------------------------------------------

    @property
    def typing(self) -> bool:
        return self.active and not self.reached_end

    def skip(self):
        """Equivalent to obj_writer's button2 skip-to-end behavior."""

        if not self.active:
            return

        if self.reached_end:
            return

        if not self.skippable or self.prevent_char_skip:
            return

        safety = 0

        while not self.reached_end and self.token_index < len(self.tokens):
            safety += 1
            if safety > 10000:
                break

            token = self.tokens[self.token_index]
            self.token_index += 1

            if token.kind == "char":
                self.visible_glyphs.append(
                    VisibleGlyph(
                        char=str(token.value),
                        color=self.current_color,
                        shake=self.profile.shake,
                        rainbow=self.rainbow,
                    )
                )
            elif token.kind == "newline":
                self.visible_glyphs.append(
                    VisibleGlyph(char="\n", color=self.current_color)
                )
            elif token.kind == "spacer":
                self.visible_glyphs.append(
                    VisibleGlyph(char=None, color=self.current_color)
                )
            elif token.kind == "command":
                command, argument = token.value
                self._handle_command(str(command), str(argument))
            elif token.kind == "halt":
                self.halt = int(token.value or 1)
                self.reached_end = True
                break
            # Pause tokens are deliberately ignored during a skip.

        if self.token_index >= len(self.tokens):
            self.reached_end = True

        self._render()
        self._on_page_finished()

    def confirm(self):
        """Advance a completed page.

        This models obj_writer's button1 path.  It does not automatically skip
        a page that is still typing; call ``skip()`` for that behavior.  A
        convenience ``advance_or_skip()`` method is provided for the project's
        current Z/Space convention.
        """

        if not self.active or not self.reached_end:
            return False

        if self.choice_request is not None:
            return False

        if self.halt == 2:
            self._finish_all()
            return True

        next_index = self.message_index + 1

        if next_index < len(self.messages):
            self._load_message(next_index)
            return True

        self._finish_all()
        return True

    def advance_or_skip(self):
        """Project-friendly Z/Space behavior: finish typing, then advance."""

        if not self.active:
            return False

        if self.typing:
            self.skip()
            return True

        return self.confirm()

    def next_message(self):
        """Explicit ``scr_nextmsg``-style page advance."""
        return self.confirm()

    def _on_page_finished(self):
        if self.current_entry is None:
            return

        if (
            self.current_entry.choices
            and self.on_choices is not None
        ):
            self.choice_request = list(
                self.current_entry.choices
            )
            self.on_choices(
                self.choice_request
            )

    def _finish_all(self):
        callback = self.on_complete
        self.stop(hide_box=self.auto_close)

        if callback is not None:
            callback()

    # --------------------------------------------------------
    # Writer commands
    # --------------------------------------------------------

    def _handle_command(self, command: str, argument: str):
        if command == "s":
            if argument == "0":
                self.skippable = False
            elif argument == "1":
                self.skippable = True

        elif command == "c":
            if argument == "0":
                self.current_color = self.profile.color
                self.rainbow = False
            elif argument == "Z":
                self.rainbow = True
            elif argument in COLOR_CODES:
                self.current_color = COLOR_CODES[argument]
                self.rainbow = False

        elif command == "T":
            typer = self._resolve_type_command(argument)
            if typer is not None:
                self.set_type(typer)

        elif command == "F":
            self.face_code = argument
            if self.box is not None and hasattr(self.box, "set_face_code"):
                self.box.set_face_code(argument)

        elif command == "E":
            self.expression_code = argument
            if self.box is not None and hasattr(self.box, "set_expression_code"):
                self.box.set_expression_code(argument)

        elif command == "C":
            if argument in ("1", "2", "3", "4"):
                self.choice_request = int(argument)

        elif command == "S":
            self._play_embedded_sound(argument)

        # I/m/O/M/v/V and any chapter-specific writer commands are exposed to
        # the game as hooks instead of being silently discarded forever.
        if self.on_command is not None:
            self.on_command(command, argument)

    def _resolve_type_command(self, argument: str) -> int | None:
        typer = TYPE_COMMANDS.get(argument)
        if typer is None:
            return None

        darkzone = int(getattr(self.game, "darkzone", 0) or 0)
        fighting = int(getattr(self.game, "fighting", 0) or 0)

        if argument == "0" and darkzone:
            return 6
        if argument == "A" and darkzone:
            return 89
        if argument == "N":
            if fighting:
                return 59
            if darkzone:
                return 56
        if argument == "B":
            if fighting:
                return 77
            if darkzone:
                return 57
        if argument == "S":
            if fighting and darkzone:
                return 47
            if darkzone:
                return 30
        if argument == "R" and fighting:
            return 45
        if argument == "L" and fighting:
            return 46
        if argument == "K" and fighting:
            return 48

        return typer

    # --------------------------------------------------------
    # Text sounds
    # --------------------------------------------------------

    @staticmethod
    def _sound_allowed_for_char(char: str) -> bool:
        # Direct translation of scr_textsound's ordinary suppression list.
        return char not in {
            " ",
            "\n",
            "^",
            "!",
            ".",
            "?",
            ",",
            ":",
            "/",
            "\\",
            "|",
            "*",
        }

    def _maybe_text_sound(self, char: str):
        if not self._sound_allowed_for_char(char):
            return

        if self.sound_timer > 0:
            return

        if self.current_voice_override is not None:
            try:
                self.current_voice_override.play()
                return
            except Exception:
                pass

        sound_name = self.profile.sound
        if not sound_name:
            return

        self._play_sound_name(sound_name)

        # scr_textsound assigns explicit cooldowns to a few special voices.
        if sound_name in {"snd_txtq", "snd_txtspam", "snd_txtsans"}:
            self.sound_timer = 2
        elif sound_name in {
            "snd_flowery_voicenoise_1",
            "snd_flowery_voicenoise_loop",
            "snd_tv_voice_short",
            "snd_txtjack_high_cute",
            "snd_txtjack_low2",
        }:
            self.sound_timer = 3

    def _find_sound_path(self, stem: str) -> Path | None:
        for suffix in (".wav", ".ogg", ".mp3"):
            candidate = SFX_DIR / f"{stem}{suffix}"
            if candidate.exists():
                return candidate
        return None

    def _play_sound_name(self, stem: str):
        path = self._find_sound_path(stem)
        if path is None:
            return

        # Prefer the project's AudioManager if it accepts a full path.
        audio = getattr(self.game, "audio", None)
        if audio is not None and hasattr(audio, "play_sfx"):
            try:
                audio.play_sfx(str(path))
                return
            except Exception:
                pass

        if pygame is None:
            return

        try:
            sound = self._sound_cache.get(path)
            if sound is None:
                sound = pygame.mixer.Sound(str(path))
                self._sound_cache[path] = sound
            sound.play()
        except Exception:
            pass

    def _play_embedded_sound(self, slot: str):
        writer_sounds = getattr(self.game, "writer_sounds", None)
        if writer_sounds is None:
            return

        try:
            sound = writer_sounds[int(slot)]
            sound.play()
        except Exception:
            pass

    # --------------------------------------------------------
    # Rendering handoff
    # --------------------------------------------------------

    def _render(self):
        if self.box is None:
            return

        self.box.set_writer_metrics(
            hspace=self.profile.hspace,
            vspace=self.profile.vspace,
            font_name=self.profile.font,
            textscale=self.profile.textscale,
        )

        self.box.set_glyphs(self.visible_glyphs)


__all__ = [
    "Dialogue",
    "DialogueWriter",
    "WriterProfile",
    "WriterToken",
    "VisibleGlyph",
    "WRITER_PROFILES",
]
