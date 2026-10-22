"""Verified editor metadata for the two DELTARUNE platform-slope sprites.

These declarations describe the *resources*, not their pixel masks. A screenshot
of a collision mask is not a substitute for the original mask bitmap. Game
integrations must load the actual exported sprite/mask for pixel-accurate
collisions. Both resources have the same size/origin/bounding rectangle, but
their collision silhouettes differ.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatSlopeSpriteMetadata:
    name: str
    width: int = 40
    height: int = 40
    origin_x: int = 0
    origin_y: int = 40
    bbox_left: int = 0
    bbox_right: int = 39
    bbox_top: int = 0
    bbox_bottom: int = 39
    bounding_box_mode: int = 0
    separate_masks: str = "Precise"
    collision_mask_description: str = ""
    transparent: bool = False
    smooth: bool = False
    preload: bool = False
    playback_speed: int = 30
    playback_speed_type: str = "FramesPerSecond"


SPR_PLAT_THINSLOPE = PlatSlopeSpriteMetadata(
    name="spr_plat_thinslope",
    collision_mask_description="thin diagonal mask (as shown in sprite editor)",
)

SPR_PLAT_SLOPE = PlatSlopeSpriteMetadata(
    name="spr_plat_slope",
    collision_mask_description="filled triangular wedge (as shown in sprite editor)",
)

PLAT_SLOPE_SPRITES = {
    SPR_PLAT_THINSLOPE.name: SPR_PLAT_THINSLOPE,
    SPR_PLAT_SLOPE.name: SPR_PLAT_SLOPE,
}

__all__ = [
    "PlatSlopeSpriteMetadata", "SPR_PLAT_THINSLOPE", "SPR_PLAT_SLOPE",
    "PLAT_SLOPE_SPRITES",
]
