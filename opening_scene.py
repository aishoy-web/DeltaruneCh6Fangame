"""Chapter 6 opening: caged SOUL, nighttime escape, and Kris's return.

This controller owns the short playable prologue that begins after either a
new file or an existing file is selected.  It deliberately keeps the missing
breakout/catching animation replaceable:

* ``spr_redwagon.png`` is the intact cage placeholder.
* ``spr_kris_room_wagon.png`` is the opened/broken cage placeholder.
* ``CATCH_SOUND`` is ``None`` until the final sound is supplied.
* ``DAY_ROOM_BACKGROUND`` supplies the daytime Kris-room art used after the
  catch sequence.

The linear portions are authored through :class:`cutscene.CutsceneMaster`.
Free SOUL control and room traversal happen while that command tape is paused
on ``wait_custom``—the same division used by Chapter 5 for gameplay inside a
larger cutscene.
"""

from __future__ import annotations

from pathlib import Path
import random
from typing import Any

from PIL import Image, ImageEnhance, ImageTk

from cutscene import CutsceneMaster


BASE_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Replaceable assets
# ---------------------------------------------------------------------------

SOUL_IMAGE = "spr_heart_0.png"
INTACT_CAGE_IMAGE = "spr_redwagon.png"
BROKEN_CAGE_IMAGE = "spr_kris_room_wagon.png"

# Daytime Kris-room art, relative to the project root. ``rooms.py`` deliberately
# retains the nighttime background because the opening begins in that version.
DAY_ROOM_BACKGROUND: str | None = (
    "room_backgrounds/Dreemurr_residence_location_Kris's_room.png"
)

# Set this to the AudioManager sound filename when the catch sound is ready.
CATCH_SOUND: str | None = None


# ---------------------------------------------------------------------------
# Scene tuning (logical 320x240 room coordinates / 30 FPS frames)
# ---------------------------------------------------------------------------

FRAME_MS = 33
NIGHT_ROOM_ID = "myroom"
HALLWAY_ROOM_ID = "myhallway"
LIVING_ROOM_ID = "torhouse"

INTRO_FADE_FRAMES = 24
ROOM_FADE_FRAMES = 8
DAY_FADE_FRAMES = 24
BLACK_HOLD_FRAMES = 15

CAGE_X = 47.0
CAGE_Y = 200.0
SOUL_START_X = CAGE_X + 10.0
SOUL_START_Y = CAGE_Y + 7.0

# The 16x16 SOUL only has a small amount of space between the wagon bars.  The
# player can wiggle in that area until enough movement effort has accumulated.
CAGE_SOUL_MIN_X = CAGE_X + 7.0
CAGE_SOUL_MAX_X = CAGE_X + 14.0
CAGE_SOUL_MIN_Y = CAGE_Y + 5.0
CAGE_SOUL_MAX_Y = CAGE_Y + 9.0

SOUL_SPEED = 1.5
SOUL_HITBOX_OFFSET = 4.0
SOUL_HITBOX_SIZE = 8.0

FIRST_CAGE_SHAKE = 35
SECOND_CAGE_SHAKE = 70
BREAKOUT_MOVEMENT_FRAMES = 105
BREAKOUT_TARGET_Y = 177.0
BREAKOUT_MOVE_FRAMES = 12

# The current living room is 707 pixels wide.  Reaching its far-right portion
# starts the placeholder Kris/catching sequence.
LIVING_ROOM_CATCH_X = 590.0
KRIS_FRONT_DOOR_X_MARGIN = 28.0
KRIS_FRONT_DOOR_Y = 145.0
KRIS_CATCH_SPEED = 5.0

DAY_KRIS_X = 155.0
DAY_KRIS_Y = 165.0
DAY_PLACEHOLDER_BRIGHTNESS = 1.45
DAY_PLACEHOLDER_COLOR = 0.82


# Canonical locations in the project's existing sprite organization.  Keeping
# this mapping separate from the filenames lets OpeningSprite continue to use
# short asset names while avoiding any need to duplicate or relocate sprites.
ASSET_LOCATIONS: dict[str, Path] = {
    SOUL_IMAGE: Path("sprites") / "player" / "player_red_soul" / SOUL_IMAGE,
    INTACT_CAGE_IMAGE: Path("sprites") / "assets" / INTACT_CAGE_IMAGE,
    BROKEN_CAGE_IMAGE: Path("sprites") / "assets" / BROKEN_CAGE_IMAGE,
}

# Some project revisions name the same SOUL artwork ``spr_heart.png``.
ASSET_ALIASES: dict[str, tuple[str, ...]] = {
    SOUL_IMAGE: ("spr_heart.png",),
}


def _asset_path(filename: str) -> Path:
    """Find an opening asset in common and nested project layouts.

    Opening assets first resolve through ``ASSET_LOCATIONS``. Recursive lookup
    remains as compatibility support for older project layouts.
    """
    requested = Path(filename)
    if requested.is_absolute() and requested.is_file():
        return requested

    project_relative = BASE_DIR / requested
    if project_relative.is_file():
        return project_relative

    names = (requested.name, *ASSET_ALIASES.get(requested.name, ()))
    canonical_relative = ASSET_LOCATIONS.get(requested.name)
    if canonical_relative is not None:
        canonical = BASE_DIR / canonical_relative
        if canonical.is_file():
            return canonical

    folders = (
        BASE_DIR,
        BASE_DIR / "sprites" / "player" / "player_red_soul",
        BASE_DIR / "sprites" / "assets",
        BASE_DIR / "sprites" / "objects",
        BASE_DIR / "sprites" / "ui",
        BASE_DIR / "room_backgrounds",
        # Conversation-workspace fallback; normal project installs use one of
        # the locations above.
        BASE_DIR / "upload",
    )
    candidates = tuple(folder / name for name in names for folder in folders)
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    wanted_names = {name.casefold() for name in names}
    for root in (BASE_DIR / "sprites", BASE_DIR / "room_backgrounds"):
        if not root.is_dir():
            continue
        for candidate in root.rglob("*"):
            if candidate.is_file() and candidate.name.casefold() in wanted_names:
                return candidate

    searched = "\n  ".join(str(path) for path in candidates)
    expected = BASE_DIR / (canonical_relative or requested)
    raise FileNotFoundError(
        f"Could not find opening asset {filename!r}. Expected it at "
        f"{expected}.\n"
        f"Searched:\n  {searched}"
    )


class OpeningSprite:
    """Small Canvas/Pillow actor used for the SOUL and wagon."""

    def __init__(
        self,
        game: Any,
        filename: str,
        x: float,
        y: float,
        *,
        tag: str,
    ) -> None:
        self.game = game
        self.x = float(x)
        self.y = float(y)
        self.visible = True
        self.tag = tag
        self.canvas_item: int | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self._last_scale: float | None = None
        self._shake_frames = 0
        self._shake_amount = 0.0
        self.set_image(filename)

    def set_image(self, filename: str) -> None:
        self.filename = filename
        self.image = Image.open(_asset_path(filename)).convert("RGBA")
        self.width = self.image.width
        self.height = self.image.height
        self._last_scale = None

    def set_position(self, x: float, y: float) -> None:
        self.x = float(x)
        self.y = float(y)

    def trigger_shake(self, frames: int = 8, amount: float = 1.0) -> None:
        self._shake_frames = max(self._shake_frames, int(frames))
        self._shake_amount = max(self._shake_amount, float(amount))

    def update(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1
            if self._shake_frames == 0:
                self._shake_amount = 0.0

    def render(self) -> None:
        scale = self.game.scale
        if self.photo is None or self._last_scale != scale:
            size = (
                max(1, round(self.width * scale)),
                max(1, round(self.height * scale)),
            )
            scaled = self.image.resize(size, Image.Resampling.NEAREST)
            self.photo = ImageTk.PhotoImage(scaled)
            self._last_scale = scale

        draw_x = self.x
        draw_y = self.y
        if self._shake_frames > 0:
            draw_x += random.choice((-self._shake_amount, self._shake_amount))
            draw_y += random.choice((-self._shake_amount, self._shake_amount))

        screen_x, screen_y = self.game.game_to_screen(draw_x, draw_y)
        state = "normal" if self.visible else "hidden"

        if self.canvas_item is None:
            self.canvas_item = self.game.canvas.create_image(
                screen_x,
                screen_y,
                image=self.photo,
                anchor="nw",
                tags=("opening_scene", self.tag),
            )
        else:
            self.game.canvas.coords(self.canvas_item, screen_x, screen_y)
            self.game.canvas.itemconfigure(
                self.canvas_item,
                image=self.photo,
                state=state,
            )

        if self.canvas_item is not None:
            self.game.canvas.tag_raise(self.canvas_item)

    def hide(self) -> None:
        self.visible = False
        if self.canvas_item is not None:
            self.game.canvas.itemconfigure(self.canvas_item, state="hidden")

    def destroy(self) -> None:
        if self.canvas_item is not None:
            self.game.canvas.delete(self.canvas_item)
            self.canvas_item = None
        self.photo = None


class SoulActor(OpeningSprite):
    def hitbox(self, x: float | None = None, y: float | None = None) -> tuple[float, float, float, float]:
        x = self.x if x is None else x
        y = self.y if y is None else y
        left = x + SOUL_HITBOX_OFFSET
        top = y + SOUL_HITBOX_OFFSET
        return (
            left,
            top,
            left + SOUL_HITBOX_SIZE,
            top + SOUL_HITBOX_SIZE,
        )


class OpeningScene:
    """State machine for the playable opening sequence."""

    FRAME_MS = FRAME_MS

    def __init__(self, game: Any) -> None:
        self.game = game
        self.active = False
        self.completed = False
        self.daytime = False
        self.phase = "idle"
        self.save_slot: Any = None
        self.save_data: Any = None
        self.is_new_file = False
        self.movement_effort = 0
        self.exit_cooldown = 0
        self._shake_stage = 0

        self.cutscene: CutsceneMaster | None = None
        self.soul: SoulActor | None = None
        self.cage: OpeningSprite | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(
        self,
        *,
        save_slot: Any = None,
        save_data: Any = None,
        is_new_file: bool = False,
    ) -> None:
        if self.active:
            return

        self.active = True
        self.completed = False
        self.daytime = False
        self.phase = "intro_fade"
        self.save_slot = save_slot
        self.save_data = save_data
        self.is_new_file = bool(is_new_file)
        self.movement_effort = 0
        self.exit_cooldown = 0
        self._shake_stage = 0

        self._hide_gameplay_ui()
        self.game.state = "opening_scene"
        self.game.transitioning = False
        self.game.fade_mode = None
        self.game.fade_alpha = 255
        self.game.camera_x = 0
        self.game.camera_y = 0

        try:
            self.game.audio.stop_music()
        except Exception:
            pass

        self.game.load_room(NIGHT_ROOM_ID, play_music=True)
        self.game.player.invisible = True
        self._set_player_canvas_visible(False)

        self.soul = SoulActor(
            self.game,
            SOUL_IMAGE,
            SOUL_START_X,
            SOUL_START_Y,
            tag="opening_soul",
        )
        self.cage = OpeningSprite(
            self.game,
            INTACT_CAGE_IMAGE,
            CAGE_X,
            CAGE_Y,
            tag="opening_cage",
        )

        self.cutscene = CutsceneMaster(
            self.game,
            owner=self,
            on_finish=self._on_cutscene_finished,
        )
        self.cutscene.register_actor("soul", self.soul)
        self.cutscene.register_actor("cage", self.cage)
        self.cutscene.register_actor("kris", self.game.player)

        self.cutscene.lerp_var(
            self.game,
            "fade_alpha",
            255,
            0,
            INTRO_FADE_FRAMES,
        )
        self.cutscene.wait(INTRO_FADE_FRAMES)
        self.cutscene.call(self._enable_caged_control)
        self.cutscene.wait_custom()

        self.game.render_static()
        self.render()

    def _hide_gameplay_ui(self) -> None:
        self.game._set_file_menu_visible(False)
        for widget in (self.game.menu, self.game.hud, self.game.dialogue_box):
            method = getattr(widget, "close", None) or getattr(widget, "hide", None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass

    def _enable_caged_control(self) -> None:
        self.phase = "caged"

    def _enable_roaming(self) -> None:
        self.phase = "roaming"
        self.exit_cooldown = 10

    def _on_cutscene_finished(self, _cutscene: CutsceneMaster) -> None:
        # Normal completion changes state in _finish_opening.  This guard only
        # handles an external cancellation cleanly.
        if self.active and self.phase != "complete":
            self.stop()

    def stop(self) -> None:
        self.active = False
        if self.soul is not None:
            self.soul.destroy()
        if self.cage is not None:
            self.cage.destroy()
        self.soul = None
        self.cage = None

    # ------------------------------------------------------------------
    # Per-frame update and control
    # ------------------------------------------------------------------
    def update(self) -> None:
        if not self.active:
            return

        if self.cage is not None:
            self.cage.update()

        if self.cutscene is not None and not self.cutscene.finished:
            self.cutscene.update()

        if self.exit_cooldown > 0:
            self.exit_cooldown -= 1

        if self.phase == "caged":
            self._update_caged_soul()
        elif self.phase == "roaming":
            self._update_roaming_soul()

        self._update_camera()
        self.render()

    def _held_directions(self) -> tuple[bool, bool, bool, bool]:
        keys = self.game.keys_pressed
        return (
            "Left" in keys,
            "Right" in keys,
            "Up" in keys,
            "Down" in keys,
        )

    def _movement_delta(self) -> tuple[float, float, bool]:
        left, right, up, down = self._held_directions()
        dx = (float(right) - float(left)) * SOUL_SPEED
        dy = (float(down) - float(up)) * SOUL_SPEED
        if dx and dy:
            diagonal = 1.0 / (2.0**0.5)
            dx *= diagonal
            dy *= diagonal
        return dx, dy, bool(left or right or up or down)

    def _update_caged_soul(self) -> None:
        if self.soul is None:
            return
        dx, dy, attempted = self._movement_delta()
        if not attempted:
            return

        self.soul.x = min(CAGE_SOUL_MAX_X, max(CAGE_SOUL_MIN_X, self.soul.x + dx))
        self.soul.y = min(CAGE_SOUL_MAX_Y, max(CAGE_SOUL_MIN_Y, self.soul.y + dy))
        self.movement_effort += 1

        if self.movement_effort >= FIRST_CAGE_SHAKE and self._shake_stage == 0:
            self._shake_stage = 1
            self.cage.trigger_shake(7, 1.0)
        elif self.movement_effort >= SECOND_CAGE_SHAKE and self._shake_stage == 1:
            self._shake_stage = 2
            self.cage.trigger_shake(10, 1.5)

        if self.movement_effort >= BREAKOUT_MOVEMENT_FRAMES:
            self._start_breakout()

    def _update_roaming_soul(self) -> None:
        if self.soul is None:
            return
        dx, dy, attempted = self._movement_delta()
        if not attempted:
            return

        moved = False
        if dx:
            new_x = self.soul.x + dx
            if self._soul_can_move_to(new_x, self.soul.y):
                self.soul.x = new_x
                moved = True
        if dy:
            new_y = self.soul.y + dy
            if self._soul_can_move_to(self.soul.x, new_y):
                self.soul.y = new_y
                moved = True

        if moved:
            self._check_room_exits()
            self._check_catch_trigger()

    def _soul_can_move_to(self, x: float, y: float) -> bool:
        left, top, right, bottom = self.soul.hitbox(x, y)
        if left < 0 or top < 0 or right > self.game.game_width or bottom > self.game.game_height:
            return False
        for wall in self.game.room.collisions:
            wall_left, wall_top, wall_right, wall_bottom = wall
            if (
                right > wall_left
                and left < wall_right
                and bottom > wall_top
                and top < wall_bottom
            ):
                return False
        return True

    # ------------------------------------------------------------------
    # Breakout and room traversal
    # ------------------------------------------------------------------
    def _start_breakout(self) -> None:
        if self.phase != "caged" or self.cutscene is None:
            return
        self.phase = "breakout"
        self.cage.trigger_shake(8, 2.0)

        # Append after the custom wait, then release it.  This is equivalent to
        # Chapter 5 adding more c_* commands before c_waitcustom_end().
        self.cutscene.wait(8)
        self.cutscene.call(self._show_broken_cage)
        self.cutscene.select("soul")
        self.cutscene.walk_direct(
            self.soul.x,
            BREAKOUT_TARGET_Y,
            BREAKOUT_MOVE_FRAMES,
            wait_for_completion=True,
        )
        self.cutscene.call(self._enable_roaming)
        self.cutscene.wait_custom()
        self.cutscene.resume_custom()

    def _show_broken_cage(self) -> None:
        if self.cage is not None:
            self.cage.set_image(BROKEN_CAGE_IMAGE)

    def _check_room_exits(self) -> None:
        if self.exit_cooldown > 0 or self.phase != "roaming":
            return
        soul_box = self.soul.hitbox()
        for room_exit in self.game.room.exits:
            exit_box = (
                room_exit.x,
                room_exit.y,
                room_exit.x + room_exit.width,
                room_exit.y + room_exit.height,
            )
            if self.game.rectangles_overlap(soul_box, exit_box):
                self._start_room_transition(room_exit)
                return

    def _start_room_transition(self, room_exit: Any) -> None:
        if self.cutscene is None or self.phase != "roaming":
            return
        self.phase = "room_transition"
        self.cutscene.lerp_var(
            self.game,
            "fade_alpha",
            self.game.fade_alpha,
            255,
            ROOM_FADE_FRAMES,
        )
        self.cutscene.wait(ROOM_FADE_FRAMES)
        self.cutscene.call(lambda: self._load_soul_room(room_exit))
        self.cutscene.lerp_var(
            self.game,
            "fade_alpha",
            255,
            0,
            ROOM_FADE_FRAMES,
        )
        self.cutscene.wait(ROOM_FADE_FRAMES)
        self.cutscene.call(self._enable_roaming)
        self.cutscene.wait_custom()
        self.cutscene.resume_custom()

    def _load_soul_room(self, room_exit: Any) -> None:
        self.game.load_room(
            room_exit.destination,
            room_exit.facing_direction,
            play_music=True,
        )
        # Exit spawn points are authored for Kris's low foot hitbox. Preserve
        # that hitbox position when the much smaller SOUL crosses the door;
        # otherwise it can spawn inside a hallway wall.
        player_hitbox_x = getattr(self.game.player, "hitbox_offset_x", 2.5)
        player_hitbox_y = getattr(self.game.player, "hitbox_offset_y", 32.0)
        self.soul.set_position(
            room_exit.spawn_x + player_hitbox_x - SOUL_HITBOX_OFFSET,
            room_exit.spawn_y + player_hitbox_y - SOUL_HITBOX_OFFSET,
        )
        self.game.camera_x = 0
        self.game.camera_y = 0
        self.game.render_static()

    def _check_catch_trigger(self) -> None:
        if self.game.room.name != LIVING_ROOM_ID or self.phase != "roaming":
            return
        trigger_x = min(
            LIVING_ROOM_CATCH_X,
            max(0.0, self.game.game_width - 70.0),
        )
        if self.soul.x >= trigger_x:
            self._start_catch_sequence()

    # ------------------------------------------------------------------
    # Kris enters, catches the SOUL, and morning begins
    # ------------------------------------------------------------------
    def _start_catch_sequence(self) -> None:
        if self.cutscene is None or self.phase != "roaming":
            return
        self.phase = "catch"

        catch_x = min(self.game.game_width - 45.0, self.soul.x + 18.0)
        catch_y = self.soul.y - 27.0

        self.cutscene.call(self._show_kris_at_front_door)
        self.cutscene.select("kris")
        self.cutscene.walk_direct(
            catch_x,
            catch_y,
            -KRIS_CATCH_SPEED,
            wait_for_completion=True,
        )
        self.cutscene.wait(4)
        self.cutscene.call(self._cut_to_black)
        self.cutscene.wait(BLACK_HOLD_FRAMES)
        self.cutscene.call(self._prepare_day_room)
        self.cutscene.lerp_var(
            self.game,
            "fade_alpha",
            255,
            0,
            DAY_FADE_FRAMES,
        )
        self.cutscene.wait(DAY_FADE_FRAMES)
        self.cutscene.call(self._finish_opening)
        self.cutscene.terminate()
        self.cutscene.resume_custom()

    def _show_kris_at_front_door(self) -> None:
        player = self.game.player
        player.room = self.game.room
        player.x = max(0.0, self.game.game_width - KRIS_FRONT_DOOR_X_MARGIN)
        player.y = KRIS_FRONT_DOOR_Y
        player.invisible = False
        player.set_facing("left")
        player.start_walking()
        self._set_player_canvas_visible(True)

    def _cut_to_black(self) -> None:
        if CATCH_SOUND:
            self.game.audio.play_sound(CATCH_SOUND)
        self.game.fade_alpha = 255
        self.soul.visible = False
        self.game.player.invisible = True
        self._set_player_canvas_visible(False)

    def _prepare_day_room(self) -> None:
        self.daytime = True
        self.phase = "day_fade"
        self.game.load_room(NIGHT_ROOM_ID, facing_direction="down", play_music=True)
        self.game.player.x = DAY_KRIS_X
        self.game.player.y = DAY_KRIS_Y
        self.game.player.room = self.game.room
        self.game.player.invisible = False
        self.game.player.set_facing("down")
        self.game.player.stop_walking()
        self._set_player_canvas_visible(True)
        if self.soul is not None:
            self.soul.hide()
        if self.cage is not None:
            self.cage.hide()
        self.game.camera_x = 0
        self.game.camera_y = 0
        self.game.render_static()
        self.game.fade_alpha = 255

    def _finish_opening(self) -> None:
        self.phase = "complete"
        self.completed = True
        self.active = False
        self.game.story_flags.add("chapter6_opening_complete")
        self.game.state = "playing"
        self.game.dialogue_blocks_movement = False
        self.game.was_moving = False
        self.game.fade_alpha = 0
        self.stop()
        self.game.render_static()
        self.game.render_dynamic()

    # ------------------------------------------------------------------
    # Rendering, camera, and room variants
    # ------------------------------------------------------------------
    def _update_camera(self) -> None:
        if self.soul is None or self.phase in {"catch", "day_fade", "complete"}:
            return
        center_x = self.soul.x + self.soul.width / 2.0
        center_y = self.soul.y + self.soul.height / 2.0
        if self.game.game_width > self.game.viewport_width:
            self.game.camera_x = max(
                0.0,
                min(
                    center_x - self.game.viewport_width / 2.0,
                    self.game.game_width - self.game.viewport_width,
                ),
            )
        else:
            self.game.camera_x = 0
        if self.game.game_height > self.game.viewport_height:
            self.game.camera_y = max(
                0.0,
                min(
                    center_y - self.game.viewport_height / 2.0,
                    self.game.game_height - self.game.viewport_height,
                ),
            )
        else:
            self.game.camera_y = 0

    def render(self) -> None:
        if not self.active and self.phase != "complete":
            return
        self.game.render_background_dynamic()

        # Draw the SOUL before the intact cage so the bars remain in front.
        if self.soul is not None:
            self.soul.render()
        if self.cage is not None:
            if self.game.room.name == NIGHT_ROOM_ID and self.cage.visible:
                self.cage.render()
            elif self.cage.canvas_item is not None:
                self.game.canvas.itemconfigure(
                    self.cage.canvas_item,
                    state="hidden",
                )

        if not self.game.player.invisible:
            self.game.player.render()
            if self.game.player.canvas_sprite is not None:
                self.game.canvas.tag_raise(self.game.player.canvas_sprite)
            self.game.player.animation.update()

        self.game.render_fade()

    def apply_room_variant(self, room_id: str, image: Image.Image) -> Image.Image:
        """Return the active visual variant without changing Room definitions."""
        if not self.daytime or room_id != NIGHT_ROOM_ID:
            return image

        if DAY_ROOM_BACKGROUND:
            day_path = BASE_DIR / DAY_ROOM_BACKGROUND
            if not day_path.exists():
                day_path = _asset_path(Path(DAY_ROOM_BACKGROUND).name)
            return Image.open(day_path).convert("RGBA")

        # Temporary daytime treatment until the final room sprite exists.
        rgba = image.convert("RGBA")
        bright = ImageEnhance.Brightness(rgba).enhance(DAY_PLACEHOLDER_BRIGHTNESS)
        return ImageEnhance.Color(bright).enhance(DAY_PLACEHOLDER_COLOR)

    def _set_player_canvas_visible(self, visible: bool) -> None:
        item = self.game.player.canvas_sprite
        if item is not None:
            self.game.canvas.itemconfigure(
                item,
                state="normal" if visible else "hidden",
            )


__all__ = [
    "CATCH_SOUND",
    "DAY_ROOM_BACKGROUND",
    "OpeningScene",
]
