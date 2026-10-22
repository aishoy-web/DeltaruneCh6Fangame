"""Python port of DELTARUNE's obj_plat_floor.

Supplied GML:
    PreCreate_0: event_inherited(); extflag = "";
    Create_0: moving_platform = false; rideable = 0; is_entity = 0;
              is_slope = 0; conveyor_hspeed = 0; quicksand = 0;
              depth = 3000; is_barrier = false;

The GameMaker object has no parent, so ``event_inherited()`` is a no-op for
this object as supplied. An optional parent_precreate callback is available
for external engine integrations, but is not required.

The editor's 'Uses physics' option is *disabled*. The physics-panel settings
are preserved as metadata, not used to simulate Box2D physics or calculate
sprite-based collision bounds.

Public event functions:
    plat_floor_precreate(instance, *, parent_precreate=None)
    plat_floor_create(instance)
    plat_floor_initialize(instance, *, parent_precreate=None)

The initializer calls PreCreate before Create, and is intended for use by
child objects whose own Create event calls ``event_inherited()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class PlatFloorPhysicsMetadata:
    density: float = 0.5
    restitution: float = 0.1
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False
    vertices: tuple = ()  # Screenshot provides no physics shape vertices.


def plat_floor_precreate(
    instance: Any, *, parent_precreate: Callable[[Any], None] | None = None
) -> None:
    """PreCreate_0: inherited PreCreate (if provided), then ``extflag``."""
    if parent_precreate is not None:
        parent_precreate(instance)
    instance.extflag = ""


def plat_floor_create(instance: Any) -> None:
    """Create_0: initialize the eight floor-property fields verbatim."""
    instance.moving_platform = False
    instance.rideable = 0
    instance.is_entity = 0
    instance.is_slope = 0
    instance.conveyor_hspeed = 0
    instance.quicksand = 0
    instance.depth = 3000
    instance.is_barrier = False


def plat_floor_initialize(
    instance: Any, *, parent_precreate: Callable[[Any], None] | None = None
) -> None:
    """Run the supplied PreCreate and Create events once, in that order.

    Use as the parent-create callback for ``obj_plat_movingplat`` when an
    engine isn't already managing GameMaker's PreCreate lifecycle itself.
    """
    plat_floor_precreate(instance, parent_precreate=parent_precreate)
    plat_floor_create(instance)


class PlatFloor:
    """Standalone floor object with the GameMaker editor's object metadata."""

    object_name = "obj_plat_floor"
    parent_object = None
    sprite_index_default = "spr_plat_thinplat"
    mask_index_default = None  # No separate mask assigned in the screenshot.
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    is_sensor = False
    collision_shape = "box"
    physics_metadata = PlatFloorPhysicsMetadata()

    def __init__(
        self,
        engine: Any,
        x: float = 0,
        y: float = 0,
        *,
        parent_precreate: Callable[[Any], None] | None = None,
    ) -> None:
        self.engine = engine
        self.x = x
        self.y = y
        self.xstart = x
        self.ystart = y
        self.visible = self.visible_default
        self.solid = self.solid_default
        self.persistent = self.persistent_default
        self.sprite_index = self.sprite_index_default
        self.mask_index = self.mask_index_default
        self.destroyed = False
        self.precreate(parent_precreate=parent_precreate)
        self.create()

    def precreate(
        self, *, parent_precreate: Callable[[Any], None] | None = None
    ) -> None:
        plat_floor_precreate(self, parent_precreate=parent_precreate)

    def create(self) -> None:
        plat_floor_create(self)


obj_plat_floor = PlatFloor

# Also provide the name usable as an existing engine's Create adapter.
obj_plat_floor_create = plat_floor_initialize

__all__ = [
    "PlatFloorPhysicsMetadata", "PlatFloor", "obj_plat_floor",
    "plat_floor_precreate", "plat_floor_create", "plat_floor_initialize",
    "obj_plat_floor_create",
]
