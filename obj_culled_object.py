"""Python port of DELTARUNE's obj_culled_object Create event.

Only the supplied Create event is implemented. This object is the parent of
obj_plat_entity, which is itself the parent of obj_plat_follower.

Its Create event initializes culling fields and ensures that exactly one
obj_culling_manager is *requested* when no manager instance exists. It does
not perform visibility/culling checks. That behavior belongs to the as-yet
unprovided obj_culling_manager code.

Integration with existing obj_plat_entity.py::

    from obj_culled_object import culled_object_create
    entity = PlatEntity(game, inherited_create=culled_object_create)

Or with an existing obj_plat_entity engine adapter::

    game.obj_culled_object_create = culled_object_create

This helper requires the engine to provide instance_exists(object_type) and
instance_create(x, y, object_type). Matching those GameMaker operations, the
object_type is resolved from engine.obj_culling_manager if present, otherwise
the symbolic name 'obj_culling_manager' is forwarded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CulledObjectPhysicsMetadata:
    """GameMaker editor physics values (simulation is NOT enabled)."""

    density: float = 0.5
    restitution: float = 0.1
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False
    vertices: tuple = ()  # No physics vertices supplied.


def culled_object_create(instance: Any) -> None:
    """Translate gml_Object_obj_culled_object_Create_0 on ``instance``.

    This intentionally does not return the newly created manager or store its
    reference: the original GML calls instance_create for its side effect.
    """
    instance.performs_culling_checks = False
    instance.cull_buffer_left = -4
    instance.cull_buffer_right = -4
    instance.cull_buffer_top = -4
    instance.cull_buffer_bottom = -4
    instance.cull_buffer = 0
    instance.is_culled = False

    engine = getattr(instance, "engine", getattr(instance, "state", instance))
    object_type = getattr(engine, "obj_culling_manager", "obj_culling_manager")

    exists = getattr(engine, "instance_exists", None)
    create = getattr(engine, "instance_create", None)
    if not callable(exists) or not callable(create):
        raise NotImplementedError(
            "obj_culled_object requires engine.instance_exists(object_type) "
            "and engine.instance_create(x, y, object_type)"
        )

    if not exists(object_type):
        create(0, 0, object_type)


class CulledObject:
    """Standalone GameMaker-style object used for engine registration."""

    object_name = "obj_culled_object"
    parent_object = None
    sprite_index_default = None
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    is_sensor = False
    collision_shape = "box"
    physics_metadata = CulledObjectPhysicsMetadata()

    def __init__(self, engine: Any, x: float = 0, y: float = 0) -> None:
        self.engine = engine
        self.x = x
        self.y = y
        self.visible = self.visible_default
        self.solid = self.solid_default
        self.persistent = self.persistent_default
        self.sprite_index = self.sprite_index_default
        self.destroyed = False
        self.create()

    def create(self) -> None:
        culled_object_create(self)


obj_culled_object = CulledObject

__all__ = (
    "CulledObject", "obj_culled_object", "CulledObjectPhysicsMetadata",
    "culled_object_create",
)
