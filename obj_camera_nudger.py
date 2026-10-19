"""Python port of DELTARUNE's ``obj_camera_nudger`` object.

Source events:
    PreCreate:
        event_inherited();
        xamt = 0;
        yamt = 0;
        lerpstrength = -4;
        mode = "Constant";
    Create:
        exit;

The class stores the original object/resource and physics metadata. It does
NOT create a physics body or implement collisions: the room/physics adapter
must register its 40x40 collision shape and expose overlapping instances via
``instance_place``, as required by ``scr_darkcameraideal.py``.

``parent_precreate`` optionally represents the inherited PreCreate event; it
is called with this instance *before* this object's defaults are assigned.
No parent event was supplied in the GML, so none is invented by default.
"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class CameraNudgerPhysics:
    """The GameMaker resource's physics settings (metadata, not a simulator)."""

    density: float = 0.5
    restitution: float = 0.5
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True


class CameraNudger:
    """A camera nudge zone usable by the Dark World camera-position helper."""

    object_name = "obj_camera_nudger"
    sprite_index = "spr_debug_40x40"
    uses_physics = True
    collision_shape = "box"
    # Local physics-shape vertices; the engine owns origin transforms/collisions.
    physics_vertices = ((0, 0), (40, 0), (40, 40), (0, 40))
    physics = CameraNudgerPhysics()

    def __init__(
        self,
        x: float = 0,
        y: float = 0,
        *,
        parent_precreate: Optional[Callable[["CameraNudger"], None]] = None,
    ) -> None:
        self.x = x
        self.y = y
        self.precreate(parent_precreate)
        self.create()

    def precreate(
        self,
        parent_precreate: Optional[Callable[["CameraNudger"], None]] = None,
    ) -> None:
        """Handle PreCreate, including the source's ``event_inherited()``."""
        if parent_precreate is not None:
            parent_precreate(self)

        self.xamt = 0
        self.yamt = 0
        self.lerpstrength = -4
        self.mode = "Constant"

    def create(self) -> None:
        """The GML Create event contains only ``exit;`` (no side effects)."""
        return None


# GameMaker-style alias, useful for resource registries.
obj_camera_nudger = CameraNudger

__all__ = ["CameraNudger", "CameraNudgerPhysics", "obj_camera_nudger"]
