"""Python port of DELTARUNE's ``obj_shakeobj_ext`` events.

Events supplied: Create, Step, Other_10 (User Event 0).
The original object has NO parent, sprite, or active physics simulation.

An activated controller stores the target's x/y, then alternates between
positive and negative x/y offsets at intervals controlled by ``shakespeed``.
Each movement tick subtracts ``shakereduct`` from BOTH independent axis
amplitudes. Negative amplitudes are clamped to zero. When both reach zero,
the controller writes the original position and destroys itself.

Engine integration (same adapter interface as obj_shakeobj.py):
* state.global_state.darkzone (or state.darkzone)
* state.i_ex(ref) or state.instance_exists(ref)
* state.resolve_instance(ref), when the target is a numeric/string ID
* optionally state.instance_destroy(shake_controller)
Call ``event_user(0)`` after setting target, then ``step()`` once per frame.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShakeObjExtPhysics:
    """GameMaker physics-panel metadata (physics is disabled for this object)."""

    density: float = 0.5
    restitution: float = 0.1
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False


class ShakeObjExt:
    """Extended x/y shake controller, faithfully ported from the supplied GML."""

    object_name = "obj_shakeobj_ext"
    sprite_index = None
    visible = True
    solid = False
    persistent = False
    parent = None
    texture_mask_id = None
    uses_physics = False
    is_sensor = False
    collision_shape = "box"
    physics_vertices = ()
    physics = ShakeObjExtPhysics()

    def __init__(self, state, x=0, y=0):
        self.state = state
        self.x = x
        self.y = y
        self.destroyed = False
        self.create()

    def create(self):
        """GML Create: assign defaults, then apply Light World reductions."""
        globals_ = getattr(self.state, "global_state", self.state)
        self.active = 0
        self.target = 0
        self.shakeamt = 10
        self.shakereduct = 2
        self.shakexamt = 10
        self.shakeyamt = 10

        if globals_.darkzone == 0:
            self.shakeamt *= 0.5
            self.shakereduct *= 0.5
            # GML intentionally does NOT halve shakexamt or shakeyamt.

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
                "Engine must provide i_ex(ref) or instance_exists(ref)"
            )
        return bool(checker(reference))

    def _target_instance(self):
        if not isinstance(self.target, (int, float, str)):
            return self.target
        resolver = getattr(self.state, "resolve_instance", None)
        if not callable(resolver):
            raise AttributeError(
                "Engine must provide resolve_instance(ref) for target IDs"
            )
        return resolver(self.target)

    def _destroy(self):
        if self.destroyed:
            return
        self.destroyed = True
        remover = getattr(self.state, "instance_destroy", None)
        if callable(remover):
            remover(self)

    def event_user(self, event_index):
        """GameMaker Other_10 is User Event 0."""
        if event_index != 0:
            raise ValueError("Only User Event 0 is present in the supplied GML")
        self.user_event_0()

    def user_event_0(self):
        """GML Other_10: activate and snapshot the target's position."""
        if self.destroyed:
            return
        if self._exists(self.target):
            target = self._target_instance()
            self.active = 1
            self.nowx = target.x
            self.nowy = target.y
        else:
            self._destroy()

    def step(self):
        """GML Step: perform at most one axis-amplitude update per frame."""
        if self.destroyed:
            return

        if self.active == 0:
            self._destroy()
            return

        if self.active == 1:
            if not self._exists(self.target):
                self._destroy()
                return

            self.timer += 1
            if self.timer >= self.shakespeed:
                self.shakexamt -= self.shakereduct
                self.shakeyamt -= self.shakereduct
                self.on *= -1

                if self.shakexamt < 0:
                    self.shakexamt = 0
                if self.shakeyamt < 0:
                    self.shakeyamt = 0

                target = self._target_instance()
                target.x = self.nowx + (self.shakexamt * self.on)
                target.y = self.nowy + (self.shakeyamt * self.on)

                if self.shakexamt <= 0 and self.shakeyamt <= 0:
                    self._destroy()

                self.timer = 0


# GameMaker resource-style alias.
obj_shakeobj_ext = ShakeObjExt

# Backward-compatible import alias from the earlier, incomplete draft.
# This resolves to EXT physics metadata (group 1) rather than obj_shakeobj's.
ShakeObjPhysics = ShakeObjExtPhysics

__all__ = [
    "ShakeObjExt", "ShakeObjExtPhysics", "ShakeObjPhysics", "obj_shakeobj_ext"
]
