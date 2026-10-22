"""Port of DELTARUNE's ``obj_shakeobj_tower`` GameMaker object.

The provided GML defines Create, Step, and Other 10 (User Event 0).
This is a seven-frame *fixed* horizontal shake: the Step event writes
[-10, +8, -6, +4, -2, 0] to the target's ``shakex`` on frames 1–6,
then destroys the shake controller on frame 7. ``shakeamt`` and
``shakereduct`` are initialized/overridable, but the supplied Step event
does not use them. No vertical shaking is performed.

Engine adapter requirements:
* ``state.global_state.darkzone`` (or ``state.darkzone``) for Create;
* ``state.i_ex(ref)`` or ``state.instance_exists(ref)`` for target checks;
* when ``target`` is an ID rather than a Python object,
  ``state.resolve_instance(ref)`` to obtain an object with ``shakex``;
* optionally ``state.instance_destroy(instance)`` to deregister the object.

For integration with ``scr_shakeobj_tower.py``, the engine's
``instance_create(x, y, obj_shakeobj_tower)`` must initialize this object
and return it *before* the helper assigns its target and calls
``event_user(0)``. Call ``step()`` once per frame.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShakeObjTowerPhysics:
    """Physics-panel values, inactive because uses_physics=False."""

    density: float = 0.5
    restitution: float = 0.1
    group: int = 0
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False


class ShakeObjTower:
    """Non-visual controller applying the original horizontal shake sequence."""

    object_name = "obj_shakeobj_tower"
    sprite_index = None
    visible = False
    solid = False
    persistent = False
    parent = None
    texture_mask_id = None
    uses_physics = False
    is_sensor = False
    collision_shape = "circle"
    physics_vertices = ()
    physics = ShakeObjTowerPhysics()

    _FRAME_SHAKES = (-10, 8, -6, 4, -2, 0)

    def __init__(self, state, x=0, y=0):
        self.state = state
        self.x = x
        self.y = y
        self.destroyed = False
        self.create()

    def create(self):
        """Reproduce ``gml_Object_obj_shakeobj_tower_Create_0``."""
        globals_ = getattr(self.state, "global_state", self.state)

        self.active = 0
        self.target = 0
        self.shakeamt = 10
        self.shakereduct = 2
        if globals_.darkzone == 0:
            self.shakeamt = 5
            self.shakereduct = 1

        self.shakespeed = 1
        self.nowx = 0
        self.nowy = 0
        self.on = 1
        self.timer = 0

    def _exists(self, reference):
        checker = getattr(self.state, "i_ex", None)
        if not callable(checker):
            checker = getattr(self.state, "instance_exists", None)
        if not callable(checker):
            raise AttributeError(
                "The engine must provide i_ex(ref) or instance_exists(ref)"
            )
        return bool(checker(reference))

    def _target_instance(self):
        """GameMaker accepts IDs and objects; Python may need a lookup."""
        if not isinstance(self.target, (str, int, float)):
            return self.target
        resolver = getattr(self.state, "resolve_instance", None)
        if not callable(resolver):
            raise AttributeError(
                "The engine must provide resolve_instance(ref) for target IDs"
            )
        return resolver(self.target)

    def _destroy(self):
        if self.destroyed:
            return
        self.destroyed = True
        destroy = getattr(self.state, "instance_destroy", None)
        if callable(destroy):
            destroy(self)

    def event_user(self, event_index):
        """Dispatch User Event 0 (``Other_10``)."""
        if event_index != 0:
            raise ValueError("Only User Event 0 is defined in the supplied GML")
        self.user_event_0()

    def user_event_0(self):
        """Activate if the target exists; otherwise destroy this controller."""
        if self.destroyed:
            return
        if self._exists(self.target):
            self.active = 1
            self.nowx = 0
            self.nowy = 0
        else:
            self._destroy()

    def step(self):
        """Perform one GameMaker Step event (regardless of ``active``)."""
        if self.destroyed:
            return
        if not self._exists(self.target):
            self._destroy()
            return

        self.timer += 1
        if 1 <= self.timer <= len(self._FRAME_SHAKES):
            self._target_instance().shakex = self._FRAME_SHAKES[self.timer - 1]
        elif self.timer == 7:
            self._destroy()


# GameMaker-resource-style alias used by scr_shakeobj_tower.py.
obj_shakeobj_tower = ShakeObjTower

__all__ = ["ShakeObjTower", "ShakeObjTowerPhysics", "obj_shakeobj_tower"]
