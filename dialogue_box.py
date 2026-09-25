from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageTk

from dialogue import VisibleGlyph
from dialogue_portrait import DialoguePortrait, PortraitDefinition


BASE_DIR = Path(__file__).resolve().parent

CURSOR_PATH = (
    BASE_DIR
    / "sprites"
    / "player"
    / "player_red_soul"
    / "spr_heartsmall.png"
)


class DialogueBox:
    """Viewport-space dialogue box and glyph renderer.

    This class owns the responsibilities that correspond most closely to
    ``obj_writer_stay``: box geometry, top/bottom side, offsets, colors,
    portraits, and rendering.  Character progression lives in
    ``dialogue.DialogueWriter``.

    The legacy ``set_text()`` API remains intact so existing game.py code can
    continue working while it is migrated to DialogueWriter.
    """

    TAG = "dialogue"
    CURSOR_TAG = "dialogue_cursor"

    # obj_writer_stay Light World defaults.
    DEFAULT_BOX_WIDTH = 288
    DEFAULT_BOX_HEIGHT_LINES = 3
    TOP_Y = 5
    SIDE_OFFSET = 155

    OUTER_X = 16
    INNER_X = 19
    INNER_Y_OFFSET = 3

    DEFAULT_HSPACE = 8
    DEFAULT_VSPACE = 18

    def __init__(self, game):
        self.game = game
        self.writer = None

        # --------------------------------------------------
        # Visibility / state
        # --------------------------------------------------
        self.visible = False
        self.cursor_visible = False
        self.draw_box = True

        # obj_writer_stay.side:
        #   0 = top
        #   1 = bottom
        self.side = 0
        self.side_override = None

        self.x_offset = 0
        self.y_offset = 0

        self.box_height_lines = self.DEFAULT_BOX_HEIGHT_LINES
        self.box_width_override = None

        self.border_color = "#ffffff"
        self.inner_color = "#000000"

        # A light-weight equivalent of writer_stay's doom lifetime.  It is
        # optional in Python; normal DialogueWriter ownership does not need it.
        self.doom = None

        # --------------------------------------------------
        # Text / writer metrics
        # --------------------------------------------------
        self.hspace = self.DEFAULT_HSPACE
        self.vspace = self.DEFAULT_VSPACE
        self.font_name = "main"
        self.textscale = 1.0
        self.default_text_color = "#ffffff"

        self.text_padding_x = 10
        self.text_padding_y = 9

        self.glyphs: list[VisibleGlyph] = []
        self._glyph_cache = {}
        self._glyph_photos = []
        self._glyph_items = []

        # --------------------------------------------------
        # Portrait state
        # --------------------------------------------------
        self.portrait_controller = DialoguePortrait(self.game, self)
        self.portrait = None
        self.portrait_photo = None
        self.portrait_width = 58
        self.portrait_gap = 0
        self.portrait_offset_x = 0
        self.portrait_offset_y = 0
        self.face_code = None
        self.expression_code = None

        # --------------------------------------------------
        # Canvas items
        # --------------------------------------------------
        self.canvas_items = []
        self.outer_box = None
        self.inner_box = None
        self.portrait_sprite = None
        self.soul_sprite = None

        # Backward-compatible aliases used by older game.py code.
        self.box_sprite = None
        self.text_sprite = None

        self.soul_source = None
        self.soul_photo = None

        if CURSOR_PATH.exists():
            try:
                self.soul_source = Image.open(CURSOR_PATH).convert("RGBA")
            except OSError:
                self.soul_source = None

    # ======================================================
    # Geometry
    # ======================================================

    @property
    def box_width(self):
        if self.box_width_override is not None:
            return float(self.box_width_override)
        return float(self.DEFAULT_BOX_WIDTH)

    @box_width.setter
    def box_width(self, value):
        # Preserve compatibility with older code that directly assigned
        # ``box_width``.  288 restores the writer_stay default.
        if value is None:
            self.box_width_override = None
        else:
            self.box_width_override = float(value)

    @property
    def box_y(self):
        return self.TOP_Y + (self.side * self.SIDE_OFFSET) + self.y_offset

    @box_y.setter
    def box_y(self, value):
        # Compatibility shim.  Old code used ~6 for top and ~161.5 for bottom.
        value = float(value)
        midpoint = self.TOP_Y + self.SIDE_OFFSET / 2
        self.side = 1 if value >= midpoint else 0
        self.y_offset = value - (
            self.TOP_Y + self.side * self.SIDE_OFFSET
        )

    @property
    def box_x(self):
        return self.OUTER_X + self.x_offset

    @box_x.setter
    def box_x(self, value):
        self.x_offset = float(value) - self.OUTER_X

    @property
    def box_height(self):
        # From obj_writer_stay Draw:
        # outer hei = 21 + (18 * boxheight), then +1 sprite scale.
        return 22 + self.DEFAULT_VSPACE * self.box_height_lines

    # ======================================================
    # Writer attachment
    # ======================================================

    def attach_writer(self, writer):
        self.writer = writer

    def set_writer_metrics(
        self,
        *,
        hspace=None,
        vspace=None,
        font_name=None,
        textscale=None,
    ):
        if hspace is not None:
            self.hspace = float(hspace)
        if vspace is not None:
            self.vspace = float(vspace)
        if font_name is not None:
            self.font_name = str(font_name)
        if textscale is not None:
            self.textscale = float(textscale)

        if self.visible:
            self.layout_widgets()

    # ======================================================
    # Widget creation
    # ======================================================

    def create_widgets(self):
        if self.outer_box is not None:
            return

        # Two filled rectangles reproduce writer_stay's 3-pixel white border
        # more faithfully than a Tk outline whose width changes with scaling.
        self.outer_box = self.game.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill=self.border_color,
            outline="",
            state="hidden",
            tags=(self.TAG,),
        )

        self.inner_box = self.game.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill=self.inner_color,
            outline="",
            state="hidden",
            tags=(self.TAG,),
        )

        self.portrait_sprite = self.game.canvas.create_image(
            0,
            0,
            anchor="nw",
            state="hidden",
            tags=(self.TAG,),
        )

        self.soul_sprite = self.game.canvas.create_image(
            0,
            0,
            anchor="center",
            state="hidden",
            tags=(self.CURSOR_TAG,),
        )

        self.box_sprite = self.outer_box
        # text_sprite used to be one Tk text object.  It is now a tag/alias;
        # callers should continue using set_text rather than configuring it.
        self.text_sprite = self.TAG

        self.canvas_items.extend(
            [
                self.outer_box,
                self.inner_box,
                self.portrait_sprite,
                self.soul_sprite,
            ]
        )

        self._refresh_soul_photo()
        self.layout_widgets()

    # ======================================================
    # Font / glyph rendering
    # ======================================================

    def _font_renderer(self):
        ui = getattr(self.game, "ui_sprites", None)

        if ui is not None:
            # Current project exposes main_font directly.
            if self.font_name in ("main", "mainbig"):
                font = getattr(ui, "main_font", None)
                if font is not None:
                    return font

            # Leave room for future fonts without requiring them today.
            candidate = getattr(ui, f"{self.font_name}_font", None)
            if candidate is not None:
                return candidate

            font = getattr(ui, "main_font", None)
            if font is not None:
                return font

        return None

    def _glyph_photo(self, char, color):
        scale = float(getattr(self.game, "scale", 1.0))
        key = (
            char,
            color,
            self.font_name,
            round(self.textscale, 4),
            round(scale, 4),
        )

        photo = self._glyph_cache.get(key)
        if photo is not None:
            return photo

        font = self._font_renderer()
        if font is None:
            return None

        try:
            photo = font.render(
                char,
                color=color,
                scale_multiplier=self.textscale,
            )
        except TypeError:
            # Older MainFont versions may not expose scale_multiplier.
            photo = font.render(char, color=color)
        except Exception:
            return None

        self._glyph_cache[key] = photo
        return photo

    def _ensure_glyph_item_count(self, count):
        while len(self._glyph_items) < count:
            item = self.game.canvas.create_image(
                0,
                0,
                anchor="nw",
                state="hidden",
                tags=(self.TAG, "dialogue_glyph"),
            )
            self._glyph_items.append(item)

    def set_glyphs(self, glyphs):
        self.glyphs = list(glyphs)
        self._render_glyphs()

    def set_text(self, text, color=None):
        """Backward-compatible plain-text entry point.

        Existing game.py typewriter code can continue feeding partial strings
        here.  They are now rendered with the project's bitmap MainFont rather
        than Tk's Determination Mono Web font.
        """

        color = color or self.default_text_color
        glyphs = []

        for char in str(text):
            if char == "\n":
                glyphs.append(VisibleGlyph(char="\n", color=color))
            else:
                glyphs.append(VisibleGlyph(char=char, color=color))

        self.set_glyphs(glyphs)

    def _text_origin(self):
        x = self.box_x + self.text_padding_x
        y = self.box_y + self.text_padding_y

        # Text reserves the face column whenever fc != 0, even if the actual
        # portrait asset has not been registered yet.  obj_writer changes
        # writingx/charline from the face state, not from sprite availability.
        if self.portrait_controller.character is not None:
            x += self.portrait_width + self.portrait_gap

        return x, y

    def _render_glyphs(self):
        if self.outer_box is None:
            return

        drawable = sum(
            1
            for glyph in self.glyphs
            if glyph.char not in (None, "\n")
        )
        self._ensure_glyph_item_count(drawable)

        origin_x, origin_y = self._text_origin()
        logical_x = origin_x
        logical_y = origin_y
        item_index = 0

        self._glyph_photos = []

        for glyph_index, glyph in enumerate(self.glyphs):
            char = glyph.char

            if char == "\n":
                logical_x = origin_x
                logical_y += self.vspace
                continue

            if char is None:
                logical_x += self.hspace
                continue

            color = glyph.color or self.default_text_color

            # Phase-1 rainbow support.  The writer architecture carries the
            # flag now; full per-frame HSV animation can be added without
            # changing dialogue data or parsing later.
            if glyph.rainbow:
                rainbow_colors = (
                    "#ff0000",
                    "#ffff00",
                    "#00ff00",
                    "#00ffff",
                    "#0000ff",
                    "#ff00ff",
                )
                color = rainbow_colors[glyph_index % len(rainbow_colors)]

            photo = self._glyph_photo(char, color)
            if photo is None:
                logical_x += self.hspace
                continue

            x, y = self.game.ui_to_screen(logical_x, logical_y)

            item = self._glyph_items[item_index]
            self.game.canvas.coords(item, x, y)
            self.game.canvas.itemconfigure(
                item,
                image=photo,
                state="normal" if self.visible else "hidden",
            )

            self._glyph_photos.append(photo)
            item_index += 1
            logical_x += self.hspace

        for item in self._glyph_items[item_index:]:
            self.game.canvas.itemconfigure(item, state="hidden", image="")

        if self.visible:
            self.game.canvas.tag_raise(self.TAG)
            if self.cursor_visible:
                self.game.canvas.tag_raise(self.CURSOR_TAG)

    # ======================================================
    # Layout
    # ======================================================

    def layout_widgets(self):
        if self.outer_box is None:
            return

        width = self.box_width
        outer_height = self.box_height

        outer_x1 = self.box_x
        outer_y1 = self.box_y
        outer_x2 = outer_x1 + width + 1
        outer_y2 = outer_y1 + outer_height

        # writer_stay inner dimensions:
        # x = 19, width = boxwidth - 5
        # y = outer + 3, height = 16 + (18 * boxheight)
        inner_x1 = outer_x1 + 3
        inner_y1 = outer_y1 + 3
        inner_x2 = inner_x1 + max(1, width - 5)
        inner_y2 = inner_y1 + (
            16 + self.DEFAULT_VSPACE * self.box_height_lines
        )

        sx1, sy1 = self.game.ui_to_screen(outer_x1, outer_y1)
        sx2, sy2 = self.game.ui_to_screen(outer_x2, outer_y2)
        ix1, iy1 = self.game.ui_to_screen(inner_x1, inner_y1)
        ix2, iy2 = self.game.ui_to_screen(inner_x2, inner_y2)

        self.game.canvas.coords(
            self.outer_box,
            sx1,
            sy1,
            sx2,
            sy2,
        )
        self.game.canvas.coords(
            self.inner_box,
            ix1,
            iy1,
            ix2,
            iy2,
        )

        self.game.canvas.itemconfigure(
            self.outer_box,
            fill=self.border_color,
        )
        self.game.canvas.itemconfigure(
            self.inner_box,
            fill=self.inner_color,
        )

        self._layout_portrait()
        self._layout_cursor()
        self._render_glyphs()

    def _refresh_soul_photo(self):
        if self.soul_source is None or self.soul_sprite is None:
            return

        scale = float(getattr(self.game, "scale", 1.0))
        width = max(1, round(self.soul_source.width * scale))
        height = max(1, round(self.soul_source.height * scale))

        scaled = self.soul_source.resize(
            (width, height),
            Image.Resampling.NEAREST,
        )
        self.soul_photo = ImageTk.PhotoImage(scaled)
        self.game.canvas.itemconfigure(
            self.soul_sprite,
            image=self.soul_photo,
        )

    def _layout_cursor(self):
        if self.soul_sprite is None:
            return

        self._refresh_soul_photo()

        soul_x = self.box_x + 9
        soul_y = self.box_y + 40
        sx, sy = self.game.ui_to_screen(soul_x, soul_y)
        self.game.canvas.coords(self.soul_sprite, sx, sy)

    # ======================================================
    # Portrait hooks
    # ======================================================

    def set_portrait(self, image):
        """Set a PIL image or filesystem path as the portrait."""

        if image is None:
            self.clear_portrait()
            return

        try:
            if isinstance(image, (str, Path)):
                image = Image.open(image).convert("RGBA")
            else:
                image = image.convert("RGBA")
        except Exception:
            return

        self.portrait = image
        self._layout_portrait()
        self._render_glyphs()

    def _layout_portrait(self):
        if self.portrait_sprite is None:
            return

        if self.portrait is None:
            self.game.canvas.itemconfigure(
                self.portrait_sprite,
                state="hidden",
                image="",
            )
            return

        scale = float(getattr(self.game, "scale", 1.0))
        logical_width = self.portrait_width

        ratio = (
            logical_width / self.portrait.width
            if self.portrait.width
            else 1.0
        )
        logical_height = max(1, round(self.portrait.height * ratio))

        scaled = self.portrait.resize(
            (
                max(1, round(logical_width * scale)),
                max(1, round(logical_height * scale)),
            ),
            Image.Resampling.NEAREST,
        )
        self.portrait_photo = ImageTk.PhotoImage(scaled)

        # scr_facechoice creates obj_face at writer.x + 8, writer.y + 5.
        # With the Light World writer origin (29, 15 + side*155), that is
        # logical (37, 20 + side*155), i.e. box + (21, 15).  Individual
        # portrait families then apply their own obj_face offsets.
        logical_x = self.box_x + 21 + self.portrait_offset_x
        logical_y = self.box_y + 15 + self.portrait_offset_y
        sx, sy = self.game.ui_to_screen(logical_x, logical_y)

        self.game.canvas.coords(self.portrait_sprite, sx, sy)
        self.game.canvas.itemconfigure(
            self.portrait_sprite,
            image=self.portrait_photo,
            state="normal" if self.visible else "hidden",
        )

    def _apply_portrait_state(self, portrait):
        self.face_code = portrait.face_code
        self.expression_code = portrait.expression
        self.portrait = portrait.image
        self.portrait_width = portrait.width
        self.portrait_offset_x = portrait.offset_x
        self.portrait_offset_y = portrait.offset_y
        self._layout_portrait()
        self._render_glyphs()

    def clear_portrait(self):
        self.portrait_controller.clear()
        self.portrait = None
        self.portrait_photo = None
        self.face_code = None
        self.expression_code = None
        self.portrait_offset_x = 0
        self.portrait_offset_y = 0

        if self.portrait_sprite is not None:
            self.game.canvas.itemconfigure(
                self.portrait_sprite,
                state="hidden",
                image="",
            )

        self._render_glyphs()

    def register_portrait(self, name, definition: PortraitDefinition):
        self.portrait_controller.register(name, definition)

    def register_static_portrait(self, name, path, **kwargs):
        self.portrait_controller.register_static(name, path, **kwargs)

    def trigger_mouth(self):
        self.portrait_controller.trigger_mouth()

    def set_face_code(self, code):
        self.face_code = code
        self.portrait_controller.set_face_code(code)

    def set_expression_code(self, code):
        self.expression_code = code
        self.portrait_controller.set_expression_code(code)

    # ======================================================
    # Visibility / lifecycle
    # ======================================================

    def show(self):
        self.create_widgets()
        self.visible = True

        if self.draw_box:
            self.game.canvas.itemconfigure(self.outer_box, state="normal")
            self.game.canvas.itemconfigure(self.inner_box, state="normal")
        else:
            self.game.canvas.itemconfigure(self.outer_box, state="hidden")
            self.game.canvas.itemconfigure(self.inner_box, state="hidden")

        if self.portrait is not None:
            self.game.canvas.itemconfigure(
                self.portrait_sprite,
                state="normal",
            )

        self.hide_cursor()
        self.layout_widgets()
        self.game.canvas.tag_raise(self.TAG)

    def hide(self):
        self.visible = False

        if self.outer_box is None:
            return

        self.game.canvas.itemconfigure(self.outer_box, state="hidden")
        self.game.canvas.itemconfigure(self.inner_box, state="hidden")
        self.game.canvas.itemconfigure(self.portrait_sprite, state="hidden")

        for item in self._glyph_items:
            self.game.canvas.itemconfigure(item, state="hidden")

        self.hide_cursor()

    def show_cursor(self):
        self.create_widgets()
        self.cursor_visible = True
        self._layout_cursor()
        self.game.canvas.itemconfigure(self.soul_sprite, state="normal")
        self.game.canvas.tag_raise(self.CURSOR_TAG)

    def hide_cursor(self):
        self.cursor_visible = False
        if self.soul_sprite is not None:
            self.game.canvas.itemconfigure(self.soul_sprite, state="hidden")


    def set_side(self, side=None):
        """Set DELTARUNE dialoguer side: 0=top, 1=bottom, None=automatic."""
        if side in (None, "any", "auto", -1):
            self.side_override = None
        elif side in (0, "top"):
            self.side_override = 0
            self.side = 0
        elif side in (1, "bottom"):
            self.side_override = 1
            self.side = 1
        else:
            raise ValueError(f"Unknown dialogue side: {side!r}")

        if self.visible:
            self.update_position()
            self.layout_widgets()

    def update_position(self):
        """Match the existing project rule using writer_stay's side system.

        Kris in the lower 40% of the viewport -> top box (side 0).
        Otherwise -> bottom box (side 1).
        """

        if self.side_override is not None:
            self.side = int(self.side_override)
            if self.visible:
                self.layout_widgets()
            return

        player = getattr(self.game, "player", None)
        if player is None:
            self.side = 0
            return

        try:
            player_center_y = (
                player.y
                + player.animation.sprite_height / 2
            )
            viewport_y = player_center_y - self.game.camera_y

            self.side = (
                0
                if viewport_y >= self.game.viewport_height * 0.6
                else 1
            )
        except Exception:
            self.side = 0

        if self.visible:
            self.layout_widgets()

    # obj_writer_stay-style optional keepalive support.
    def keep_alive(self, frames=2):
        self.doom = max(1, int(frames))

    def update(self):
        # obj_face Step runs independently of writer timing.
        self.portrait_controller.update()

        if self.doom is None:
            return

        self.doom -= 1
        if self.doom <= 0:
            self.doom = None
            self.hide()

    # ======================================================
    # Compatibility / input
    # ======================================================

    def advance(self):
        """Delegate advancement to the attached DialogueWriter when present."""

        if self.writer is not None and getattr(self.writer, "active", False):
            return self.writer.advance_or_skip()

        # Temporary bridge for the pre-DialogueWriter game.py.
        advance = getattr(self.game, "advance_dialogue", None)
        if callable(advance):
            return advance()

        return False

    def render_static(self):
        self.create_widgets()
        self.layout_widgets()


__all__ = ["DialogueBox", "PortraitDefinition"]
