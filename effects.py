import re
from pathlib import Path

import pygame
from PIL import Image, ImageTk


BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# ASSET SEARCH LOCATIONS
# ============================================================

# We do not need to hard-code the exact extracted sprite folder.
# EffectManager will search these locations for the requested
# sprite name.
SPRITE_SEARCH_ROOTS = (
    BASE_DIR / "sprites",
    BASE_DIR / "assets" / "sprites",
)

SFX_SEARCH_ROOTS = (
    BASE_DIR / "sfx",
    BASE_DIR / "assets" / "sfx",
)


# ============================================================
# EMOTE SPRITES
# ============================================================

# Based on scr_emote().
EMOTE_SPRITES = {
    "!": "spr_exc",
    "?": "spr_emote_questionmark",
    "...": "spr_emote_ellipsis",
    "note": "spr_musblc",
}


# ============================================================
# HELPERS
# ============================================================

def _natural_sort_key(path):
    """
    Sort filenames containing numbers naturally.

    Example:
        spr_exc_2.png
        spr_exc_10.png
    """

    parts = re.split(
        r"(\d+)",
        path.stem,
    )

    return [
        int(part)
        if part.isdigit()
        else part.lower()
        for part in parts
    ]


# ============================================================
# GENERIC SPRITE EFFECT
# ============================================================

class SpriteEffect:
    """
    Generic temporary world sprite.

    This is the Python equivalent of the useful behavior we
    get from things such as:

        scr_marker()
        scr_doom()

    It handles:

        - world position
        - animation
        - scaling
        - lifetime
        - depth value
        - Tkinter Canvas rendering
        - destruction
    """

    def __init__(
        self,
        manager,
        sprite,
        x,
        y,
        *,
        image_index=0.0,
        image_speed=0.0,
        xscale=1.0,
        yscale=1.0,
        depth=None,
        depth_offset=0,
        lifetime=None,
    ):
        self.manager = manager
        self.game = manager.game

        # ----------------------------------------------------
        # Sprite
        # ----------------------------------------------------

        self.sprite = sprite

        self.frames = (
            self.manager.get_sprite_frames(
                sprite
            )
        )

        if not self.frames:
            raise ValueError(
                f"No frames loaded for effect sprite "
                f"{sprite!r}"
            )

        self.sprite_width = (
            self.frames[0].width
        )

        self.sprite_height = (
            self.frames[0].height
        )

        # ----------------------------------------------------
        # World position
        # ----------------------------------------------------

        self.x = float(x)
        self.y = float(y)

        # ----------------------------------------------------
        # Animation
        # ----------------------------------------------------

        self.image_index = float(
            image_index
        )

        self.image_speed = float(
            image_speed
        )

        # ----------------------------------------------------
        # Scale
        # ----------------------------------------------------

        self.xscale = float(xscale)
        self.yscale = float(yscale)

        # ----------------------------------------------------
        # Depth
        #
        # DELTARUNE scr_depth():
        #
        # depth = 100000 -
        #     (
        #         y * 10
        #         + sprite_height * 10
        #         + offset * 10
        #     )
        # ----------------------------------------------------

        self.depth_offset = float(
            depth_offset
        )

        if depth is None:
            self.depth = (
                self.calculate_depth()
            )
        else:
            self.depth = float(depth)

        # ----------------------------------------------------
        # Lifetime
        # ----------------------------------------------------

        self.lifetime = (
            None
            if lifetime is None
            else max(
                0,
                int(lifetime),
            )
        )

        self.age = 0
        self.finished = False

        # ----------------------------------------------------
        # Canvas
        # ----------------------------------------------------

        self.canvas_item = None

        self._photos = []
        self._photo_scale_key = None

        self.refresh_photos()
        self.create_canvas_item()

    # ========================================================
    # DEPTH
    # ========================================================

    def calculate_depth(self):
        """
        Equivalent to:

        scr_depth(id, depth_offset)
        """

        return 100000 - (
            (self.y * 10)
            + (self.sprite_height * 10)
            + (self.depth_offset * 10)
        )

    # ========================================================
    # LIFETIME
    # ========================================================

    def doom(
        self,
        frames,
    ):
        """
        Equivalent in purpose to:

            scr_doom(instance, frames)

        Unlike GameMaker, Python does not need a separate
        obj_doom timer object.
        """

        self.lifetime = max(
            0,
            int(frames),
        )

        self.age = 0

        return self

    # ========================================================
    # TKINTER IMAGE CREATION
    # ========================================================

    def refresh_photos(self):
        """
        Rebuild Tkinter images when fullscreen scale or effect
        scale changes.
        """

        screen_scale = float(
            getattr(
                self.game,
                "scale",
                1,
            )
        )

        scale_key = (
            screen_scale,
            self.xscale,
            self.yscale,
        )

        if (
            scale_key
            == self._photo_scale_key
            and self._photos
        ):
            return

        self._photo_scale_key = scale_key

        self._photos = []

        for source_frame in self.frames:

            frame = source_frame

            # ----------------------------------------------
            # Handle negative scaling / sprite flipping.
            # ----------------------------------------------

            if self.xscale < 0:
                frame = frame.transpose(
                    Image.Transpose.FLIP_LEFT_RIGHT
                )

            if self.yscale < 0:
                frame = frame.transpose(
                    Image.Transpose.FLIP_TOP_BOTTOM
                )

            width = max(
                1,
                round(
                    frame.width
                    * screen_scale
                    * abs(self.xscale)
                ),
            )

            height = max(
                1,
                round(
                    frame.height
                    * screen_scale
                    * abs(self.yscale)
                ),
            )

            frame = frame.resize(
                (
                    width,
                    height,
                ),
                Image.Resampling.NEAREST,
            )

            self._photos.append(
                ImageTk.PhotoImage(
                    frame
                )
            )

    # ========================================================
    # CANVAS
    # ========================================================

    def create_canvas_item(self):

        if not self._photos:
            return

        screen_x, screen_y = (
            self.manager.world_to_screen(
                self.x,
                self.y,
            )
        )

        self.canvas_item = (
            self.game.canvas.create_image(
                screen_x,
                screen_y,
                anchor="nw",
                image=self._photos[0],
                tags=(
                    "world_effect",
                    "effects",
                ),
            )
        )

        self.manager.apply_depth(
            self
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self):

        if self.finished:
            return

        # ----------------------------------------------------
        # Animation
        #
        # GameMaker's image_speed is effectively added to
        # image_index each game step.
        # ----------------------------------------------------

        if len(self.frames) > 1:

            self.image_index += (
                self.image_speed
            )

            self.image_index %= len(
                self.frames
            )

        # ----------------------------------------------------
        # Lifetime
        # ----------------------------------------------------

        if self.lifetime is not None:

            self.age += 1

            if self.age >= self.lifetime:

                self.finish()
                return

        self.render()

    # ========================================================
    # RENDER
    # ========================================================

    def render(self):

        if self.canvas_item is None:
            return

        self.refresh_photos()

        if not self._photos:
            return

        frame_index = int(
            self.image_index
        )

        frame_index %= len(
            self._photos
        )

        self.game.canvas.itemconfigure(
            self.canvas_item,
            image=self._photos[
                frame_index
            ],
        )

        # ----------------------------------------------------
        # The effect does NOT follow its actor.
        #
        # However, because x/y are WORLD coordinates, the
        # Canvas position must still respond to camera motion.
        # ----------------------------------------------------

        screen_x, screen_y = (
            self.manager.world_to_screen(
                self.x,
                self.y,
            )
        )

        self.game.canvas.coords(
            self.canvas_item,
            screen_x,
            screen_y,
        )

        self.manager.apply_depth(
            self
        )

    # ========================================================
    # FINISH / DESTROY
    # ========================================================

    def finish(self):
        self.finished = True

    def destroy(self):

        if self.canvas_item is not None:

            self.game.canvas.delete(
                self.canvas_item
            )

            self.canvas_item = None

        self._photos.clear()


# ============================================================
# EMOTE EFFECT
# ============================================================

class EmoteEffect(SpriteEffect):
    """
    DELTARUNE-style character emote.

    Based on:

        scr_emote()
        obj_excblcon Create
        obj_excblcon Step
        obj_excblcon Alarm 0

    Normal behavior:

        image_speed = 0.1
        lifetime = 20 steps

    Light World:
        scale = 1

    Dark World:
        scale = 2
    """

    DEFAULT_DURATION = 20
    DEFAULT_IMAGE_SPEED = 0.1

    def __init__(
        self,
        manager,
        actor,
        kind,
        *,
        duration=DEFAULT_DURATION,
        x_offset=None,
        y_offset=0,
    ):
        if kind not in EMOTE_SPRITES:

            raise ValueError(
                f"Unknown emote type: "
                f"{kind!r}"
            )

        self.actor = actor
        self.kind = kind

        sprite = (
            EMOTE_SPRITES[kind]
        )

        dark_multiplier = (
            manager.get_dark_multiplier()
        )

        sprite_width, _ = (
            manager.get_sprite_size(
                sprite
            )
        )

        x, y = (
            self.calculate_emote_position(
                manager,
                actor,
                sprite_width,
                dark_multiplier,
                x_offset,
                y_offset,
            )
        )

        super().__init__(
            manager=manager,
            sprite=sprite,
            x=x,
            y=y,
            image_speed=(
                self.DEFAULT_IMAGE_SPEED
            ),
            xscale=dark_multiplier,
            yscale=dark_multiplier,
            lifetime=duration,
        )

    # ========================================================
    # SCR_EMOTE POSITIONING
    # ========================================================

    @staticmethod
    def calculate_emote_position(
        manager,
        actor,
        emote_width,
        dark_multiplier,
        x_offset,
        y_offset,
    ):
        """
        Recreation of the positioning rules from scr_emote().

        Position is calculated ONCE when the bubble is created.
        The bubble does not continue following the actor.
        """

        actor_x = float(
            getattr(
                actor,
                "x",
                0,
            )
        )

        actor_y = float(
            getattr(
                actor,
                "y",
                0,
            )
        )

        sprite_width = (
            manager.get_actor_sprite_width(
                actor
            )
        )

        anchor_x = (
            manager.get_actor_xoffset(
                actor
            )
        )

        image_xscale = float(
            getattr(
                actor,
                "image_xscale",
                1,
            )
        )

        # scr_emote():
        #
        # __emotexoff = 10 * __dmult
        #
        # unless argument[2] is supplied.

        if x_offset is None:

            x_offset = (
                10
                * dark_multiplier
            )

        # scr_emote():
        #
        # bubble.y =
        #     y - (10 * dark_multiplier)
        #
        # then add optional y offset.

        y = (
            actor_y
            - (
                10
                * dark_multiplier
            )
            + y_offset
        )

        # Equivalent of GameMaker sign().
        sign_x = (
            1
            if image_xscale >= 0
            else -1
        )

        # ----------------------------------------------------
        # Direct translation of scr_emote()'s horizontal
        # positioning.
        # ----------------------------------------------------

        if image_xscale > 0:

            x = (
                (
                    actor_x
                    - (
                        anchor_x
                        * image_xscale
                    )
                )
                + (
                    (sprite_width / 2)
                    * sign_x
                )
                - (emote_width / 2)
                + x_offset
            )

        else:

            x = (
                (
                    actor_x
                    + (
                        anchor_x
                        * image_xscale
                    )
                )
                - (
                    (sprite_width / 2)
                    * sign_x
                )
                - (emote_width / 2)
                + x_offset
            )

        return x, y

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self):

        if self.finished:
            return

        # ----------------------------------------------------
        # obj_excblcon Step:
        #
        # if button3_h():
        #     create marker copy
        #     copy visual state
        #     scr_doom(copy, 2)
        #     destroy original
        #
        # We support the behavior but deliberately do not
        # guess whether button3 should be Z, X, or C.
        # ----------------------------------------------------

        if self.manager.emote_skip_held():

            self.create_short_tail()
            self.finish()

            return

        super().update()

    # ========================================================
    # SHORT TAIL
    # ========================================================

    def create_short_tail(self):
        """
        Reproduce obj_excblcon's two-step visual remnant.
        """

        tail = (
            self.manager.marker(
                self.x,
                self.y,
                self.sprite,
                image_index=(
                    self.image_index
                ),
                image_speed=(
                    self.image_speed
                ),
                xscale=(
                    self.xscale
                ),
                yscale=(
                    self.yscale
                ),
                depth=(
                    self.depth
                ),
            )
        )

        self.manager.doom(
            tail,
            2,
        )


# ============================================================
# EFFECT MANAGER
# ============================================================

class EffectManager:
    """
    Central manager for temporary world/cutscene effects.

    Game should create exactly one:

        self.effects = EffectManager(self)

    Then call:

        self.effects.update()

    once per game update.
    """

    def __init__(
        self,
        game,
    ):
        self.game = game

        self.effects = []

        # ----------------------------------------------------
        # Asset caches
        # ----------------------------------------------------

        self._sprite_frames = {}
        self._sprite_paths = {}

        self._sounds = {}
        self._sound_paths = {}

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self):

        for effect in self.effects[:]:

            effect.update()

            if effect.finished:

                effect.destroy()

                self.effects.remove(
                    effect
                )

    # ========================================================
    # GENERIC MARKER
    # ========================================================

    def marker(
        self,
        x,
        y,
        sprite,
        *,
        image_index=0.0,
        image_speed=0.0,
        xscale=1.0,
        yscale=1.0,
        depth=None,
        depth_offset=0,
        lifetime=None,
    ):
        """
        General equivalent of scr_marker().

        GML scr_marker() defaults image_speed to 0.
        """

        effect = SpriteEffect(
            manager=self,
            sprite=sprite,
            x=x,
            y=y,
            image_index=image_index,
            image_speed=image_speed,
            xscale=xscale,
            yscale=yscale,
            depth=depth,
            depth_offset=depth_offset,
            lifetime=lifetime,
        )

        self.effects.append(
            effect
        )

        return effect

    # ========================================================
    # SCR_DOOM
    # ========================================================

    def doom(
        self,
        effect,
        frames,
    ):
        """
        Equivalent in purpose to:

            scr_doom(effect, frames)
        """

        if effect is None:
            return None

        effect.doom(
            frames
        )

        return effect

    # ========================================================
    # EMOTE
    # ========================================================

    def emote(
        self,
        actor,
        kind,
        *,
        duration=20,
        x_offset=None,
        y_offset=0,
    ):
        """
        Equivalent in purpose to scr_emote().

        This function does NOT automatically play sound.
        """

        actor = self.resolve_actor(
            actor
        )

        if actor is None:
            return None

        effect = EmoteEffect(
            manager=self,
            actor=actor,
            kind=kind,
            duration=duration,
            x_offset=x_offset,
            y_offset=y_offset,
        )

        self.effects.append(
            effect
        )

        return effect

    # ========================================================
    # CONVENIENCE EMOTES
    # ========================================================

    def exclaim(
        self,
        actor,
        *,
        duration=20,
        sound=True,
        x_offset=None,
        y_offset=0,
    ):
        """
        Standard DELTARUNE alert reaction:

            spr_exc
            +
            snd_b

        Sound can be disabled while keeping the visual.
        """

        if sound:
            self.play_sound(
                "snd_b"
            )

        return self.emote(
            actor,
            "!",
            duration=duration,
            x_offset=x_offset,
            y_offset=y_offset,
        )

    def question(
        self,
        actor,
        *,
        duration=20,
        x_offset=None,
        y_offset=0,
    ):

        return self.emote(
            actor,
            "?",
            duration=duration,
            x_offset=x_offset,
            y_offset=y_offset,
        )

    def ellipsis(
        self,
        actor,
        *,
        duration=20,
        x_offset=None,
        y_offset=0,
    ):

        return self.emote(
            actor,
            "...",
            duration=duration,
            x_offset=x_offset,
            y_offset=y_offset,
        )

    def note(
        self,
        actor,
        *,
        duration=20,
        x_offset=None,
        y_offset=0,
    ):

        return self.emote(
            actor,
            "note",
            duration=duration,
            x_offset=x_offset,
            y_offset=y_offset,
        )

    # ========================================================
    # ACTOR RESOLUTION
    # ========================================================

    def resolve_actor(
        self,
        actor,
    ):
        """
        Accept either:

            actual actor object

        or:

            "kris"

        This can be expanded later when the cutscene actor
        registry is finalized.
        """

        if not isinstance(
            actor,
            str,
        ):
            return actor

        name = actor.lower()

        if name == "kris":

            return getattr(
                self.game,
                "player",
                None,
            )

        # ----------------------------------------------------
        # Future cutscene actor registry support.
        # ----------------------------------------------------

        for owner_name in (
            "cutscene",
            "cutscene_master",
        ):

            owner = getattr(
                self.game,
                owner_name,
                None,
            )

            if owner is None:
                continue

            getter = getattr(
                owner,
                "get_actor",
                None,
            )

            if callable(getter):

                found = getter(
                    name
                )

                if found is not None:
                    return found

        return None

    # ========================================================
    # ACTOR SPRITE GEOMETRY
    # ========================================================

    def get_actor_sprite_width(
        self,
        actor,
    ):
        """
        Try the GameMaker-like field first, then fall back to
        common names used by Python sprite classes.
        """

        for attribute in (
            "sprite_width",
            "frame_width",
            "width",
        ):

            value = getattr(
                actor,
                attribute,
                None,
            )

            if value is not None:
                return float(value)

        # Kris' current implementation may expose a PIL image.
        for attribute in (
            "image",
            "current_image",
            "sprite",
        ):

            image = getattr(
                actor,
                attribute,
                None,
            )

            if hasattr(
                image,
                "width",
            ):
                return float(
                    image.width
                )

        return 0.0

    def get_actor_xoffset(
        self,
        actor,
    ):
        """
        Equivalent concept to sprite_get_xoffset().
        """

        for attribute in (
            "sprite_xoffset",
            "xoffset",
            "sprite_offset_x",
            "offset_x",
        ):

            value = getattr(
                actor,
                attribute,
                None,
            )

            if value is not None:
                return float(value)

        return 0.0

    # ========================================================
    # DARK WORLD MULTIPLIER
    # ========================================================

    def get_dark_multiplier(self):
        """
        scr_emote():

            __dmult = 1 + global.darkzone
        """

        darkzone = getattr(
            self.game,
            "darkzone",
            0,
        )

        return (
            2
            if bool(darkzone)
            else 1
        )

    # ========================================================
    # BUTTON3 HOOK
    # ========================================================

    def emote_skip_held(self):
        """
        DELTARUNE's obj_excblcon checks button3_h().

        We know the behavior but have not established which
        physical fangame key should represent button3.

        Therefore this method only uses an existing logical
        input hook if one has been implemented elsewhere.
        """

        # Game-level hook.
        callback = getattr(
            self.game,
            "button3_held",
            None,
        )

        if callable(callback):
            return bool(
                callback()
            )

        # Input-manager hooks.
        for name in (
            "input",
            "input_manager",
        ):

            manager = getattr(
                self.game,
                name,
                None,
            )

            if manager is None:
                continue

            callback = getattr(
                manager,
                "button3_held",
                None,
            )

            if callable(callback):

                return bool(
                    callback()
                )

        # Do not guess Z/X/C.
        return False

    # ========================================================
    # WORLD -> SCREEN
    # ========================================================

    def world_to_screen(
        self,
        x,
        y,
    ):
        """
        Convert logical world coordinates into actual Tkinter
        Canvas coordinates.

        Prefer the Game's own world_to_screen() implementation
        when one exists.
        """

        converter = getattr(
            self.game,
            "world_to_screen",
            None,
        )

        if callable(converter):

            return converter(
                x,
                y,
            )

        # ----------------------------------------------------
        # Fallback using camera position + ui_to_screen().
        # ----------------------------------------------------

        camera_x = float(
            getattr(
                self.game,
                "camera_x",
                0,
            )
        )

        camera_y = float(
            getattr(
                self.game,
                "camera_y",
                0,
            )
        )

        camera = getattr(
            self.game,
            "camera",
            None,
        )

        if camera is not None:

            camera_x = float(
                getattr(
                    camera,
                    "x",
                    camera_x,
                )
            )

            camera_y = float(
                getattr(
                    camera,
                    "y",
                    camera_y,
                )
            )

        logical_x = (
            x - camera_x
        )

        logical_y = (
            y - camera_y
        )

        converter = getattr(
            self.game,
            "ui_to_screen",
            None,
        )

        if callable(converter):

            return converter(
                logical_x,
                logical_y,
            )

        # ----------------------------------------------------
        # Last-resort direct scaling.
        # ----------------------------------------------------

        scale = float(
            getattr(
                self.game,
                "scale",
                1,
            )
        )

        offset_x = float(
            getattr(
                self.game,
                "offset_x",
                0,
            )
        )

        offset_y = float(
            getattr(
                self.game,
                "offset_y",
                0,
            )
        )

        return (
            offset_x
            + logical_x * scale,
            offset_y
            + logical_y * scale,
        )

    # ========================================================
    # DEPTH / CANVAS STACKING
    # ========================================================

    def apply_depth(
        self,
        effect,
    ):
        """
        Store DELTARUNE-compatible logical depth now.

        If Game later gains a central world-depth sorter, this
        method is the single place that needs to connect to it.
        """

        sorter = getattr(
            self.game,
            "apply_depth_to_canvas_item",
            None,
        )

        if callable(sorter):

            sorter(
                effect.canvas_item,
                effect.depth,
            )

            return

        # Current fallback:
        #
        # temporary effects remain above ordinary world
        # Canvas items.
        #
        # The effect still retains its correct logical depth,
        # so this can later plug into proper depth sorting
        # without changing SpriteEffect or EmoteEffect.

        if effect.canvas_item is not None:

            self.game.canvas.tag_raise(
                effect.canvas_item
            )

    # ========================================================
    # SPRITE LOADING
    # ========================================================

    def get_sprite_frames(
        self,
        sprite,
    ):
        """
        Return cached PIL frames.

        Supports:

            spr_exc.png

        as well as extracted sequences such as:

            spr_exc_0.png
            spr_exc_1.png
            spr_exc_2.png
        """

        key = str(sprite)

        if key in self._sprite_frames:

            return self._sprite_frames[
                key
            ]

        files = (
            self.find_sprite_files(
                sprite
            )
        )

        frames = []

        for path in files:

            with Image.open(path) as image:

                frame_count = int(
                    getattr(
                        image,
                        "n_frames",
                        1,
                    )
                )

                for index in range(
                    frame_count
                ):

                    if frame_count > 1:
                        image.seek(index)

                    frames.append(
                        image.convert(
                            "RGBA"
                        ).copy()
                    )

        self._sprite_frames[
            key
        ] = frames

        return frames

    def get_sprite_size(
        self,
        sprite,
    ):

        frames = self.get_sprite_frames(
            sprite
        )

        if not frames:
            return 0, 0

        return (
            frames[0].width,
            frames[0].height,
        )

    def find_sprite_files(
        self,
        sprite,
    ):
        """
        Locate a standalone extracted sprite or numbered
        extracted frames.
        """

        key = str(sprite)

        if key in self._sprite_paths:

            return self._sprite_paths[
                key
            ]

        direct_path = Path(
            key
        )

        if direct_path.is_file():

            result = [
                direct_path
            ]

            self._sprite_paths[
                key
            ] = result

            return result

        sprite_name = (
            direct_path.stem
            if direct_path.suffix
            else key
        )

        # ----------------------------------------------------
        # Prefer a numbered frame sequence when one exists.
        # ----------------------------------------------------

        numbered = []

        for root in SPRITE_SEARCH_ROOTS:

            if not root.exists():
                continue

            numbered.extend(
                root.rglob(
                    f"{sprite_name}_*.png"
                )
            )

        if numbered:

            result = sorted(
                set(numbered),
                key=_natural_sort_key,
            )

            self._sprite_paths[
                key
            ] = result

            return result

        # ----------------------------------------------------
        # Otherwise use the standalone file.
        # ----------------------------------------------------

        extensions = (
            ".png",
            ".gif",
            ".webp",
        )

        for root in SPRITE_SEARCH_ROOTS:

            if not root.exists():
                continue

            for extension in extensions:

                matches = list(
                    root.rglob(
                        f"{sprite_name}"
                        f"{extension}"
                    )
                )

                if matches:

                    result = [
                        matches[0]
                    ]

                    self._sprite_paths[
                        key
                    ] = result

                    return result

        raise FileNotFoundError(
            "Could not locate effect sprite "
            f"{sprite_name!r} under:\n"
            + "\n".join(
                str(root)
                for root
                in SPRITE_SEARCH_ROOTS
            )
        )

    # ========================================================
    # AUDIO
    # ========================================================

    def play_sound(
        self,
        sound_name,
    ):
        """
        Play a sound effect.

        exclaim() uses this for snd_b.
        """

        sound = self.get_sound(
            sound_name
        )

        if sound is not None:
            sound.play()

    def get_sound(
        self,
        sound_name,
    ):

        key = str(
            sound_name
        )

        if key in self._sounds:
            return self._sounds[key]

        path = self.find_sound(
            sound_name
        )

        if path is None:
            return None

        try:

            sound = pygame.mixer.Sound(
                str(path)
            )

        except pygame.error as exc:

            print(
                "[effects] Could not load "
                f"{path}: {exc}"
            )

            return None

        self._sounds[key] = sound

        return sound

    def find_sound(
        self,
        sound_name,
    ):
        """
        Locate snd_b regardless of whether the extracted file
        is WAV, OGG, etc.
        """

        key = str(
            sound_name
        )

        if key in self._sound_paths:

            return self._sound_paths[
                key
            ]

        path = Path(
            key
        )

        if path.is_file():

            self._sound_paths[
                key
            ] = path

            return path

        sound_stem = (
            path.stem
            if path.suffix
            else key
        )

        extensions = (
            ".wav",
            ".ogg",
            ".mp3",
        )

        for root in SFX_SEARCH_ROOTS:

            if not root.exists():
                continue

            for extension in extensions:

                matches = list(
                    root.rglob(
                        f"{sound_stem}"
                        f"{extension}"
                    )
                )

                if matches:

                    self._sound_paths[
                        key
                    ] = matches[0]

                    return matches[0]

        print(
            "[effects] Sound not found: "
            f"{sound_name}"
        )

        return None

    # ========================================================
    # CLEANUP
    # ========================================================

    def clear(self):
        """
        Destroy every currently active effect.

        Useful when changing rooms or resetting a scene.
        """

        for effect in self.effects:

            effect.destroy()

        self.effects.clear()