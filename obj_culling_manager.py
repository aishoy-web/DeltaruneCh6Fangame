"""Python port of DELTARUNE's ``obj_culling_manager`` (Pre Draw event 76).

This is *visibility bookkeeping*, not an instance-destruction routine: it sets
``is_culled`` on eligible instances every Pre Draw, leaving drawing/stepping
behavior to the objects themselves.

Required engine interface:
    * ``instance_exists(obj_type)``
    * ``iter_instances(obj_type)`` (or ``instances_of`` / ``get_instances``)
    * ``camera_get_view_x(camera)`` and ``camera_get_view_y(camera)`` with
      ``view_camera[0]`` when no ``obj_plat_camera`` exists.

IMPORTANT: iterating ``obj_culled_object`` must include instances of its
*descendant* object types, as GameMaker's ``with (obj_culled_object)`` does.
An engine whose registry matches only exact object types must implement that
inheritance-aware lookup; this helper cannot infer arbitrary object trees.

To access an existing ``obj_plat_camera``, the engine must return its live
instance through the iterable lookup, ``instance_find(type, 0)``, or the
resource attribute itself. Numeric instance IDs may be resolved through
``resolve_instance(id)`` if applicable.

The original viewport is hardcoded to 640 by 480; this is deliberately NOT
replaced with the current window size. Boundary comparisons are strict.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VIEW_WIDTH = 640
VIEW_HEIGHT = 480
NO_INSTANCE = -4


@dataclass(frozen=True)
class CullingManagerPhysicsMetadata:
    """GameMaker editor metadata (built-in physics is disabled)."""

    density: float = 0.5
    restitution: float = 0.1
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False
    vertices: tuple = ()


def _resource(engine: Any, object_name: str) -> Any:
    return getattr(engine, object_name, object_name)


def _iter_instances(engine: Any, resource: Any):
    """Implement GML ``with (object)`` via the engine's registry."""
    for name in ("iter_instances", "instances_of", "get_instances"):
        fn = getattr(engine, name, None)
        if callable(fn):
            return iter(fn(resource))
    raise NotImplementedError(
        "obj_culling_manager requires engine.iter_instances(object_type) "
        "(or instances_of/get_instances) with descendant-aware lookups"
    )


def _camera_instance(engine: Any, camera_ref: Any) -> Any:
    """Resolve the first obj_plat_camera instance without inventing coordinates."""
    # The resource itself may be a live instance in a small Python engine.
    if (not isinstance(camera_ref, (str, int, float, type))
            and hasattr(camera_ref, "x") and hasattr(camera_ref, "y")):
        return camera_ref

    find = getattr(engine, "instance_find", None)
    if callable(find):
        found = find(camera_ref, 0)
        if found not in (None, 0, NO_INSTANCE, -1):
            if hasattr(found, "x") and hasattr(found, "y"):
                return found
            resolve = getattr(engine, "resolve_instance", None)
            if callable(resolve):
                obj = resolve(found)
                if obj is not None and hasattr(obj, "x") and hasattr(obj, "y"):
                    return obj

    for instance in _iter_instances(engine, camera_ref):
        return instance

    raise LookupError(
        "obj_plat_camera exists but its instance could not be retrieved"
    )


def _camera_top_left(engine: Any) -> tuple[float, float]:
    camera_ref = _resource(engine, "obj_plat_camera")
    exists = getattr(engine, "instance_exists", None)
    if not callable(exists):
        raise NotImplementedError(
            "obj_culling_manager requires engine.instance_exists(obj_plat_camera)"
        )

    if exists(camera_ref):
        plat_camera = _camera_instance(engine, camera_ref)
        return plat_camera.x - VIEW_WIDTH / 2, plat_camera.y - VIEW_HEIGHT / 2

    try:
        camera = engine.view_camera[0]
    except (AttributeError, IndexError, TypeError) as exc:
        raise NotImplementedError(
            "No obj_plat_camera: engine.view_camera[0] is required"
        ) from exc

    get_x = getattr(engine, "camera_get_view_x", None)
    get_y = getattr(engine, "camera_get_view_y", None)
    if not callable(get_x) or not callable(get_y):
        raise NotImplementedError(
            "No obj_plat_camera: camera_get_view_x/y adapters are required"
        )
    return get_x(camera), get_y(camera)


def _outside_view(obj: Any, cx: float, cy: float) -> bool:
    """Direct transcription of the GML's four strict disjunctions."""
    return (
        obj.bbox_right + max(obj.cull_buffer, obj.cull_buffer_right) < cx
        or obj.bbox_left - max(obj.cull_buffer, obj.cull_buffer_left) > cx + VIEW_WIDTH
        or obj.bbox_bottom + max(obj.cull_buffer, obj.cull_buffer_bottom) < cy
        or obj.bbox_top - max(obj.cull_buffer, obj.cull_buffer_top) > cy + VIEW_HEIGHT
    )


def culling_manager_pre_draw(manager: Any) -> None:
    """``gml_Object_obj_culling_manager_Draw_76`` on a manager instance."""
    engine = getattr(manager, "engine", manager)
    cx, cy = _camera_top_left(engine)

    # GameMaker's `with (obj_culled_object)` also selects child instances.
    for obj in _iter_instances(engine, _resource(engine, "obj_culled_object")):
        if obj.performs_culling_checks:
            obj.is_culled = _outside_view(obj, cx, cy)

    # These two explicit object groups are checked even without the flag.
    for object_name in ("obj_fusuma_door", "obj_overworld_foxbullet"):
        for obj in _iter_instances(engine, _resource(engine, object_name)):
            obj.is_culled = _outside_view(obj, cx, cy)


class CullingManager:
    """GameMaker-style manager for the Python overworld's Pre Draw phase."""

    object_name = "obj_culling_manager"
    parent_object = None
    sprite_index_default = None
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    is_sensor = False
    collision_shape = "box"
    physics_metadata = CullingManagerPhysicsMetadata()

    def __init__(self, engine: Any, x: float = 0, y: float = 0):
        self.engine = engine
        self.x = x
        self.y = y
        self.sprite_index = self.sprite_index_default
        self.visible = self.visible_default
        self.solid = self.solid_default
        self.persistent = self.persistent_default
        self.destroyed = False

    def pre_draw(self) -> None:
        culling_manager_pre_draw(self)

    # Both names are provided for engine event-dispatch compatibility.
    def draw_76(self) -> None:
        self.pre_draw()

    def draw_pre(self) -> None:
        self.pre_draw()


obj_culling_manager = CullingManager

__all__ = (
    "VIEW_WIDTH", "VIEW_HEIGHT", "CullingManagerPhysicsMetadata",
    "CullingManager", "obj_culling_manager", "culling_manager_pre_draw",
)
