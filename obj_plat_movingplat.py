"""Python port of DELTARUNE ``obj_plat_movingplat``.

Source: Create_0, Step_1 (Begin Step), Step_2 (End Step), Draw_0.

GameMaker object inheritance: obj_plat_movingplat -> obj_plat_floor.
The parent obj_plat_floor has now been ported. A supplied ``parent_create``
callback or ``engine.obj_plat_floor_create`` takes precedence; otherwise the
standalone Python port calls ``plat_floor_initialize`` directly (PreCreate
then Create).

The game engine must:
  * Dispatch Begin Step BEFORE normal Step and End Step.
  * Maintain ``xprevious``/``yprevious`` as the *previous frame's* positions.
  * Provide inheritance-aware ``iter_instances(obj_plat_entity)`` (or an
    equivalent method), including descendants such as obj_plat_follower.
  * Supply snap-to-ground and drawing adapters, plus object destruction.

The supplied GML does not use GameMaker's built-in physics engine even though
its editor contains physics metadata. These fields are kept only as metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sin
from typing import Any, Callable

from scr_plat_set_difference import scr_plat_set_difference
from obj_plat_floor import plat_floor_initialize


@dataclass(frozen=True)
class MovingPlatformPhysicsMetadata:
    density: float = 0.5
    restitution: float = 0.1
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False
    vertices: tuple = ()


def _engine(obj: Any) -> Any:
    return getattr(obj, "engine", obj)


def _resource(engine: Any, name: str) -> Any:
    return getattr(engine, name, name)


def _iter_entities(platform: Any):
    """Translate ``with (obj_plat_entity)`` using descendant-aware lookup."""
    engine = _engine(platform)
    resource = _resource(engine, "obj_plat_entity")
    for method_name in ("iter_instances", "instances_of", "get_instances"):
        method = getattr(engine, method_name, None)
        if callable(method):
            # Snapshot avoids registry-mutation surprises inside snap callbacks.
            return tuple(method(resource))
    raise NotImplementedError(
        "obj_plat_movingplat requires engine.iter_instances(obj_plat_entity) "
        "(or instances_of/get_instances), including child object instances"
    )


def _snap_rider(rider: Any, engine: Any) -> None:
    """Call existing per-entity or engine snap adapters, retaining GML context."""
    callback = getattr(rider, "scr_plat_snap_to_ground", None)
    if callable(callback):
        callback()
        return

    callback = getattr(engine, "scr_plat_snap_to_ground", None)
    if callable(callback):
        callback(rider)
        return

    # Standalone direct port (requires the collision adapters of that helper).
    from scr_plat_snap_to_ground import scr_plat_snap_to_ground
    scr_plat_snap_to_ground(rider)


def _is_riding(rider: Any, platform: Any) -> bool:
    """GML compares rider.ground to ``other.id``, not coordinates or names."""
    reference = getattr(rider, "ground", None)
    identity = getattr(platform, "id", platform)
    # Support both native object-reference and integer-ID Python registries.
    return reference is platform or reference == identity


def movingplat_create(platform: Any, *, parent_create: Callable | None = None) -> None:
    """Create_0: inherited floor initialization, then supplied defaults."""
    if parent_create is not None:
        parent_create(platform)
    else:
        adapter = getattr(_engine(platform), "obj_plat_floor_create", None)
        if callable(adapter):
            adapter(platform)
        else:
            plat_floor_initialize(platform)

    platform.moving_platform = True
    platform.dif_x = 0
    platform.dif_y = 0
    platform.dif_type = 0
    platform.movetype = 1
    platform.ax = 50
    platform.ay = 40
    platform.fx = 0.0825
    platform.fy = 0.08
    platform.t = 0


def movingplat_begin_step(platform: Any) -> None:
    """Step_1 (Begin Step): move first, then snap all riders to new surface."""
    if getattr(platform, "destroyed", False):
        return

    engine = _engine(platform)
    globals_ = getattr(engine, "global_state", engine)
    paused = bool(getattr(globals_, "pause_plat", False))

    if not paused:
        platform.t += 1
        if platform.movetype == 1:
            platform.x = platform.xstart + sin(platform.fx * platform.t) * platform.ax
            platform.y = platform.ystart + sin(platform.fy * platform.t) * platform.ay
        elif platform.movetype == 2:
            platform.x = platform.xstart + sin(platform.fx * platform.t) * platform.ax
            platform.y += 2
            try:
                room_height = engine.room_height
            except AttributeError as exc:
                raise NotImplementedError(
                    "movetype 2 requires engine.room_height"
                ) from exc
            if platform.y > room_height + 100:
                platform._destroy()
        # Other movetype values increment t but leave x and y unchanged.

    # This block is OUTSIDE the pause check in the original GML.
    # Thus riders are snapped even when global.pause_plat is true.
    for rider in _iter_entities(platform):
        if _is_riding(rider, platform):
            _snap_rider(rider, engine)


def movingplat_end_step(platform: Any) -> None:
    """Step_2 (End Step): run the previously ported movement-difference helper."""
    if getattr(platform, "destroyed", False):
        return

    bound = getattr(platform, "scr_plat_set_difference", None)
    if callable(bound):
        bound()
        return
    engine_callback = getattr(_engine(platform), "scr_plat_set_difference", None)
    if callable(engine_callback):
        engine_callback(platform)
        return
    scr_plat_set_difference(platform)


def movingplat_draw(platform: Any) -> None:
    """Draw_0: use the renderer's GameMaker-like ``draw_self()``."""
    callback = getattr(platform, "draw_self", None)
    if callable(callback):
        callback()
        return
    callback = getattr(_engine(platform), "draw_self", None)
    if callable(callback):
        callback(platform)
        return
    raise NotImplementedError("obj_plat_movingplat requires draw_self()")


class PlatMovingPlat:
    """Independent object adapter; floor parent is loaded by default."""

    object_name = "obj_plat_movingplat"
    parent_object = "obj_plat_floor"
    sprite_index_default = "spr_plat_thinplat"
    mask_index_default = None  # No override configured in GameMaker editor.
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    is_sensor = False
    collision_shape = "box"
    physics_metadata = MovingPlatformPhysicsMetadata()

    def __init__(self, engine: Any, x: float = 0, y: float = 0, *,
                 parent_create: Callable | None = None,
                 xstart: float | None = None, ystart: float | None = None):
        self.engine = engine
        self.x = x
        self.y = y
        self.xstart = x if xstart is None else xstart
        self.ystart = y if ystart is None else ystart
        self.xprevious = x
        self.yprevious = y
        self.hspeed = 0
        self.vspeed = 0
        self.visible = self.visible_default
        self.solid = self.solid_default
        self.persistent = self.persistent_default
        self.sprite_index = self.sprite_index_default
        self.mask_index = self.mask_index_default
        self.destroyed = False
        # Assigned by the runtime's instance registry, when applicable.
        # Object identity is used if no numeric ID is supplied.
        self.create(parent_create=parent_create)

    def create(self, *, parent_create: Callable | None = None) -> None:
        movingplat_create(self, parent_create=parent_create)

    def _destroy(self) -> None:
        if self.destroyed:
            return
        self.destroyed = True
        remove = getattr(self.engine, "instance_destroy", None)
        if not callable(remove):
            raise NotImplementedError(
                "obj_plat_movingplat requires engine.instance_destroy(instance)"
            )
        remove(self)

    def begin_step(self) -> None:
        movingplat_begin_step(self)

    def end_step(self) -> None:
        movingplat_end_step(self)

    def draw(self) -> None:
        movingplat_draw(self)


obj_plat_movingplat = PlatMovingPlat

__all__ = [
    "MovingPlatformPhysicsMetadata", "PlatMovingPlat", "obj_plat_movingplat",
    "movingplat_create", "movingplat_begin_step", "movingplat_end_step",
    "movingplat_draw",
]
