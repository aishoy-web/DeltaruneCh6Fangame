"""GameMaker ``obj_solidblock`` resource metadata for the Chapter 6 fangame.

The supplied GameMaker object has NO events and NO parent.  Consequently this
module deliberately adds no Create, Step, collision, or interaction behavior.
Its constructor only supplies ordinary Python instance scaffolding; a running
engine must perform sprite-mask collision queries and handle inheritance-aware
object-family searches.

``obj_interactablesolid`` is a subclass of this object, but replaces its
sprite (``spr_interactable``) and visibility (False).  Neither class is a
subclass of ``obj_interactable`` in the original GameMaker project.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SolidSmallSpriteMetadata:
    """Verified fields from the supplied ``spr_solidsmall`` editor screenshot.

    These are LOCAL sprite bounds, not world-space collision coordinates.
    The physics editor's Circle shape is unrelated to the sprite's rectangular
    collision mask, because the GameMaker physics checkbox is disabled.
    """

    name: str = "spr_solidsmall"
    width: int = 20
    height: int = 20
    origin_x: int = 0
    origin_y: int = 0
    bbox_left: int = 0
    bbox_top: int = 0
    bbox_right: int = 19
    bbox_bottom: int = 19
    mask_type: str = "axis_aligned_rectangle"
    playback_speed: int = 1
    playback_speed_type: str = "frames_per_game_frame"


@dataclass(frozen=True)
class SolidBlockPhysicsMetadata:
    """Editor-only physics values; NOT a mandate to enable Box2D physics."""

    density: float = 0.5
    restitution: float = 0.1
    group: int = 0
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False
    vertices: tuple = ()


SPR_SOLIDSMALL = SolidSmallSpriteMetadata()


class SolidBlock:
    """Eventless base object for collision-family membership.

    In particular, the name does NOT mean GameMaker's built-in ``solid``
    checkbox is enabled: its editor setting is False.  Membership in the
    ``obj_solidblock`` family is separate from that flag.
    """

    object_name = "obj_solidblock"
    parent_object = None
    sprite_index_default = "spr_solidsmall"
    sprite_metadata = SPR_SOLIDSMALL
    mask_index_default = None  # No separate collision-mask sprite assigned.
    visible_default = False
    solid_default = False
    persistent_default = False
    uses_physics = False
    is_sensor = False
    collision_shape = "circle"  # Disabled Box2D editor setting.
    physics_metadata = SolidBlockPhysicsMetadata()

    def __init__(
        self,
        game: Any,
        x: float = 0,
        y: float = 0,
        *,
        image_xscale: float = 1.0,
        image_yscale: float = 1.0,
    ) -> None:
        # Python runtime instance scaffolding, NOT a GameMaker Create event.
        # Class-attribute lookup is dynamic: children keep their own sprite,
        # visibility, and other editor overrides when they call super().__init__.
        self.game = game
        self.x = x
        self.y = y
        self.image_xscale = image_xscale
        self.image_yscale = image_yscale
        self.sprite_index = self.sprite_index_default
        self.mask_index = self.mask_index_default
        self.visible = self.visible_default
        self.solid = self.solid_default
        self.persistent = self.persistent_default


obj_solidblock = SolidBlock

__all__ = [
    "SolidBlock",
    "SolidSmallSpriteMetadata",
    "SolidBlockPhysicsMetadata",
    "SPR_SOLIDSMALL",
    "obj_solidblock",
]
