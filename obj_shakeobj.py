"""Python port of DELTARUNE's ``obj_shakeobj`` GameMaker object.

Source events: Create, Step, and Other_10 (User Event 0).

Unlike ``obj_shakeobj_tower``, this controller moves the target's actual
``x`` coordinate instead of setting ``target.shakex``. Each active Step
reduces shakeamt, reverses the direction, and sets target.x relative to the
position saved by User Event 0. ``y`` is not modified.

Engine interface:
* ``state.global_state.darkzone`` (or ``state.darkzone``).
* ``state.i_ex(ref)`` or ``state.instance_exists(ref)`` to check targets.
* ``state.resolve_instance(ref)`` if targets are stored as numeric/string IDs.
* Optional ``state.instance_destroy(controller)`` for removal from the world.

The game engine should call ``step()`` once per frame. The object's physics
panel settings are metadata only; GameMaker physics is disabled.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShakeObjPhysics:
    density: float = 0.5
    restitution: float = 0.1
    group: int = 0
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False


class ShakeObj:
    """Shake controller using the supplied GameMaker event implementations."""

    object_name = "obj_shakeobj"
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
    physics = ShakeObjPhysics()

    def __init__(self, state, x=0, y=0):
        self.state = state
        self.x = x
        self.y = y
        self.destroyed = False
        self.create()

    def create(self):
        """GML Create: set default parameters, with Light World overrides."""
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
                "Engine must provide i_ex(ref) or instance_exists(ref)"
            )
        return bool(checker(reference))

    def _target_instance(self):
        """Resolve GameMaker-style numeric IDs, or return a Python object."""
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
        """Dispatch the supplied Other_10 event (GameMaker User Event 0)."""
        if event_index != 0:
            raise ValueError("Only User Event 0 is defined for obj_shakeobj")
        self.user_event_0()

    def user_event_0(self):
        """GML Other_10: save the target's position and enable shaking."""
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
        """GML Step: alternate shrinking horizontal offsets each frame."""
        if self.destroyed:
            return

        if self.active == 0:
            self._destroy()
            return

        if self.active == 1:
            if not self._exists(self.target):
                self._destroy()
                return

            self.shakeamt -= self.shakereduct
            self.on *= -1
            self._target_instance().x = self.nowx + (self.shakeamt * self.on)

            if self.shakeamt <= 0:
                self._destroy()


obj_shakeobj = ShakeObj

__all__ = ["ShakeObj", "ShakeObjPhysics", "obj_shakeobj"]
