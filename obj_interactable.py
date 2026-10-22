"""Python port of GameMaker's obj_interactable (Chapter 6 fangame).

Source GML -- Other / User Event 0 only::

    if (variable_instance_exists(id, "on_interact"))
        on_interact();

This object has no Create, Step, collision, proximity, or input events in the
supplied source. Something ELSE must invoke ``event_user(0)``. A descendant
with its own User Event 0 overrides this callback dispatcher unless it
explicitly invokes the inherited handler, matching GameMaker event semantics.
"""
from __future__ import annotations

from typing import Any, Callable


_MISSING = object()


def interactable_user_event_0(instance: Any) -> Any:
    """Run the parent's optional on_interact callback on *instance*.

    A missing callback is a no-op. A present non-callable value is deliberately
    not ignored: the GML attempts to call it and would raise an error.

    Class-defined Python methods are also supported as callback equivalents to
    functions attached to GameMaker instances.
    """
    callback = getattr(instance, "on_interact", _MISSING)
    if callback is _MISSING:
        return None
    return callback()


class Interactable:
    """Generic, optionally callback-driven GameMaker interactable.

    The metadata reproduces the object editor configuration. The physics
    collision-shape setting doesn't activate Box2D: ``uses_physics`` is False.
    This class intentionally does not poll keys or detect player proximity.
    """

    object_name = "obj_interactable"
    parent_object = None
    sprite_index_default = None
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    collision_shape = "circle"

    def __init__(
        self,
        game: Any,
        x: float = 0,
        y: float = 0,
        *,
        on_interact: Callable[[], Any] | object = _MISSING,
    ) -> None:
        # These fields represent the Python engine's generic instance
        # container, not any additional GameMaker Create-event logic.
        self.game = game
        self.x = x
        self.y = y
        self.visible = self.visible_default
        if on_interact is not _MISSING:
            self.on_interact = on_interact

    def user_event_0(self) -> Any:
        """Equivalent of obj_interactable's Other_10 / User Event 0."""
        return interactable_user_event_0(self)

    def event_user(self, index: int) -> Any:
        """Dispatch only the event supplied by the source GML."""
        if index != 0:
            raise NotImplementedError(
                f"obj_interactable supplies only User Event 0 (got {index})"
            )
        # Dynamic dispatch is deliberate: if a child overrides user_event_0,
        # the child implementation runs instead of the parent's event.
        return self.user_event_0()


obj_interactable = Interactable

__all__ = ["Interactable", "interactable_user_event_0", "obj_interactable"]
