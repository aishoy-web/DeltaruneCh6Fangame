"""Python port of DELTARUNE ``obj_plat_block`` (editor data only).

No events are defined on this object. In GameMaker it inherits the PreCreate
and Create events of ``obj_plat_floor``. The Python subclass does likewise,
with the block's own sprite and editor settings.

Collision bounds MUST come from the runtime's ``spr_plat_grid`` collision mask,
not from the disabled GameMaker physics-panel information.
"""
from __future__ import annotations

from obj_plat_floor import PlatFloor, PlatFloorPhysicsMetadata


class PlatBlock(PlatFloor):
    object_name = "obj_plat_block"
    parent_object = "obj_plat_floor"
    sprite_index_default = "spr_plat_grid"
    mask_index_default = None
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    is_sensor = False
    collision_shape = "box"
    physics_metadata = PlatFloorPhysicsMetadata()


obj_plat_block = PlatBlock

__all__ = ["PlatBlock", "obj_plat_block"]
