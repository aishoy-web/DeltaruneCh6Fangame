"""Faithful Python port of DELTARUNE's ``obj_plat_slope``.

Supplied GameMaker events:

* Create_0: set floor-like properties, ``is_slope=1``, ``plattype=0``;
  define ``set_slope()`` and call it.
* Other_4 (Room Start): call ``set_slope()`` again.
* Draw_0: ``draw_self()``.

``obj_plat_slope`` has **no GameMaker parent**. In particular its Create
code does NOT initialize ``extflag`` or ``is_barrier`` like ``obj_plat_floor``.
The optional sprite dimension overrides are intended for a runtime's loaded
sprite metadata and for unit tests. Neither the GameMaker editor's disabled
physics settings nor the screenshot preview determine actual collision bounds.

The geometry uses *unscaled* ``sprite_width`` and ``sprite_height``. Even a
negative ``image_xscale`` does not mirror ``x1``/``x2``; the ground-snapping
script handles choosing the correct entity bounding-box side.
"""
from __future__ import annotations

from typing import Any

from obj_plat_floor import PlatFloorPhysicsMetadata
from plat_slope_sprite_metadata import SPR_PLAT_THINSLOPE


def _engine(instance: Any) -> Any:
    return getattr(instance, "engine", instance)


def _sprite_dimension(instance: Any, dimension: str) -> float:
    """Use the current sprite size, without inventing a fallback rectangle."""
    value = getattr(instance, f"sprite_{dimension}", None)
    if value is not None:
        return value

    engine = _engine(instance)
    sprite = getattr(instance, "sprite_index", None)
    getter = getattr(engine, f"sprite_get_{dimension}", None)
    if callable(getter):
        return getter(sprite)

    # Optional integration adapter for sprite managers returning (width,height).
    get_size = getattr(engine, "get_sprite_size", None)
    if callable(get_size):
        return get_size(sprite)[0 if dimension == "width" else 1]

    raise NotImplementedError(
        f"obj_plat_slope requires sprite_{dimension} on the instance or a "
        f"sprite_get_{dimension}(sprite_index) engine method "
        "(alternatively get_sprite_size(sprite_index))."
    )


def plat_slope_set_slope(instance: Any) -> None:
    """GML's Create-defined ``set_slope()``; recompute all five fields."""
    width = _sprite_dimension(instance, "width")
    height = _sprite_dimension(instance, "height")
    instance.x1 = instance.x
    instance.y1 = instance.y
    instance.x2 = instance.x + width
    instance.y2 = instance.y - height
    # Preserve GML's literal slope calculation, including zero-width failure.
    instance.m = (instance.y2 - instance.y1) / (instance.x2 - instance.x1)


def plat_slope_create(instance: Any) -> None:
    """Create_0. The source has no event_inherited() call."""
    instance.moving_platform = False
    instance.rideable = 0
    instance.is_entity = 0
    instance.is_slope = 0
    instance.conveyor_hspeed = 0
    instance.quicksand = 0
    instance.depth = 3000
    instance.is_slope = 1
    instance.plattype = 0
    plat_slope_set_slope(instance)


def plat_slope_room_start(instance: Any) -> None:
    """Other_4 (Room Start): recalculate geometry."""
    plat_slope_set_slope(instance)


def plat_slope_draw(instance: Any) -> None:
    """Draw_0: forward to the renderer's ``draw_self`` operation."""
    draw = getattr(instance, "draw_self", None)
    if callable(draw):
        draw()
        return
    draw = getattr(_engine(instance), "draw_self", None)
    if callable(draw):
        draw(instance)
        return
    raise NotImplementedError("obj_plat_slope requires draw_self() on the object or engine")


class PlatSlope:
    """Standalone engine adapter for ``obj_plat_slope`` (no parent class)."""

    object_name = "obj_plat_slope"
    parent_object = None
    sprite_index_default = "spr_plat_thinslope"
    sprite_metadata = SPR_PLAT_THINSLOPE  # From supplied sprite-editor screenshot.
    mask_index_default = None
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
        sprite_width: float | None = None,
        sprite_height: float | None = None,
    ) -> None:
        self.engine = engine
        self.x = x
        self.y = y
        self.xstart = x
        self.ystart = y
        self.sprite_index = self.sprite_index_default
        self.mask_index = self.mask_index_default
        self.visible = self.visible_default
        self.solid = self.solid_default
        self.persistent = self.persistent_default
        self.image_xscale = 1
        self.image_yscale = 1
        self.destroyed = False
        if sprite_width is not None:
            self.sprite_width = sprite_width
        if sprite_height is not None:
            self.sprite_height = sprite_height
        self.create()

    def create(self) -> None:
        plat_slope_create(self)

    def set_slope(self) -> None:
        plat_slope_set_slope(self)

    def room_start(self) -> None:
        plat_slope_room_start(self)

    def draw(self) -> None:
        plat_slope_draw(self)


obj_plat_slope = PlatSlope

__all__ = [
    "PlatSlope", "obj_plat_slope", "plat_slope_create",
    "plat_slope_set_slope", "plat_slope_room_start", "plat_slope_draw",
]
