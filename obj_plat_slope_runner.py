"""Python port of GameMaker ``obj_plat_slope_runner``.

Object editor:
    Parent: obj_plat_slope
    Sprite: spr_plat_slope (40x40, origin 0,40)
    Mask: default sprite mask (precise, triangular wedge)
    Visible: true; Solid: false; Persistent: false; Uses physics: false
    Collision shape (disabled Box2D settings): box

No events of its own: Create, Room Start, and Draw are inherited directly
from ``obj_plat_slope``. Do not add a separate Create event or call its
initialization twice.
"""
from __future__ import annotations

from typing import Any

from obj_plat_slope import PlatSlope
from plat_slope_sprite_metadata import SPR_PLAT_SLOPE


class PlatSlopeRunner(PlatSlope):
    """An event-free slope child with a different sprite/mask resource.

    ``sprite_width`` and ``sprite_height`` default to the exact 40x40 editor
    metadata. Explicit overrides are available for engine integration/tests.
    The engine still must provide the *pixel collision mask* independently.
    """

    object_name = "obj_plat_slope_runner"
    parent_object = "obj_plat_slope"
    sprite_index_default = SPR_PLAT_SLOPE.name
    sprite_metadata = SPR_PLAT_SLOPE

    def __init__(
        self,
        engine: Any,
        x: float = 0,
        y: float = 0,
        *,
        sprite_width: float | None = None,
        sprite_height: float | None = None,
    ) -> None:
        super().__init__(
            engine,
            x=x,
            y=y,
            sprite_width=(self.sprite_metadata.width
                          if sprite_width is None else sprite_width),
            sprite_height=(self.sprite_metadata.height
                           if sprite_height is None else sprite_height),
        )


obj_plat_slope_runner = PlatSlopeRunner

__all__ = ["PlatSlopeRunner", "obj_plat_slope_runner"]
