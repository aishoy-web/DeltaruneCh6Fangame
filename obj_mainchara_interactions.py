"""Source-grounded obj_mainchara interaction logic for the Chapter 6 fangame.

Ported from the interaction portion of obj_mainchara's normal Step event,
plus its Alarm[1] event. This is *not* a complete port of obj_mainchara's
movement, rendering, camera, or battle functionality.

The `scr_interact()` implementation is now known: it sets the target's
`myinteract = 1` and then triggers `event_user(0)`. This module defaults to
the port from `scr_interact.py`. An explicit callback may still be injected
for engine-specific dispatch or older integrations.

Expect a GameMaker-compatible collision callback with the signature:
    collision_rectangle(x1, y1, x2, y2, object_type, precise, notme)
It must return an instance or -4/None, and should include descendant types.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from scr_interact import scr_interact as _scr_interact

NOONE = -4
INTERACTABLE = "obj_interactable"
INTERACTABLE_SOLID = "obj_interactablesolid"

FACING_DOWN = 0
FACING_RIGHT = 1
FACING_UP = 2
FACING_LEFT = 3

# GML uses sprite dimensions WITHOUT image_xscale, and d=darkzone+1.
# These are rectangle coordinates, not pixel distances to an object's center.
@dataclass(frozen=True)
class InteractionRect:
    x1: float
    y1: float
    x2: float
    y2: float

    def normalized(self) -> "InteractionRect":
        """Convenience for a Python AABB engine; never applied before GML calls."""
        return InteractionRect(min(self.x1, self.x2), min(self.y1, self.y2),
                               max(self.x1, self.x2), max(self.y1, self.y2))


def _has_instance(value: Any) -> bool:
    # GameMaker's -4 means 'no instance'. Python fixtures often use None.
    return value is not None and value != NOONE


def mainchara_interaction_rectangle(
    player: Any, facing: int, darkzone: int, *, lookup: bool = True
) -> InteractionRect:
    """Return the exact facing-dependent rectangle from obj_mainchara Step.

    IMPORTANT: For FACING_UP, the first GML `collision_rectangle` checks
    x+3, but the second lookup checks x+(3*d). Both are retained here via
    the `lookup` flag. This discrepancy matters for Dark World collisions.
    """
    x, y = player.x, player.y
    w, h = player.sprite_width, player.sprite_height
    d = darkzone + 1
    if facing == FACING_RIGHT:
        return InteractionRect(x + w / 2, y + 6*d + h / 2,
                               x + w + 13*d, y + h)
    if facing == FACING_LEFT:
        return InteractionRect(x + w / 2, y + 6*d + h / 2,
                               x - 13*d, y + h)
    if facing == FACING_DOWN:
        return InteractionRect(x + 4*d, y + 28*d,
                               x + w - 4*d, y + h + 15*d)
    if facing == FACING_UP:
        return InteractionRect(x + (3*d if lookup else 3), y + h - 5*d,
                               x + w - 5*d, y + 5*d)
    raise ValueError(f"Unknown facing direction {facing!r}; expected 0, 1, 2, or 3")


def user_event_0_adapter(target: Any) -> Any:
    """Legacy event-only adapter (does NOT initialize myinteract).

    Prefer the real scr_interact() from scr_interact.py. Kept solely for
    compatibility with older integration code and tests.
    """
    return target.event_user(0)


def mainchara_alarm_1(player: Any, *, state: Any) -> None:
    """Exact source for obj_mainchara Alarm[1]."""
    if state.interact == 1:
        state.interact = 0


def decrement_interaction_buffer(player: Any) -> None:
    """GML decrements onebuffer once, near the end of obj_mainchara Step.

    The host game should call this only if it does NOT already decrement
    `onebuffer` in its own Step implementation.
    """
    player.onebuffer -= 1


def mainchara_try_interact(
    player: Any,
    *,
    state: Any,
    confirm_pressed: bool,
    collision_rectangle: Callable[[float, float, float, float, Any, bool, bool], Any],
    scr_interact: Callable[[Any], Any] = _scr_interact,
    interactable_type: Any = INTERACTABLE,
    solid_type: Any = INTERACTABLE_SOLID,
) -> Any | None:
    """Run the `onebuffer < 0` section from obj_mainchara's Step.

    Preserve the two-phase GML query (`if collision_rectangle(...)`, then
    lookup again), priority of obj_interactablesolid over obj_interactable,
    inverse target facing, and the player's `interactedobject` reference.

    `scr_interact` is invoked *inside the target context* in GML. By
    default, the port assigns `target.myinteract = 1` then invokes its
    `event_user(0)`; callers may pass another dispatcher if necessary.

    `interactable_type`/`solid_type` can be set to the engine's actual
    class/resource handles; the string defaults are test-friendly names.

    The return value is the selected target or None; it does not assert that
    the target accepted the interaction or that dialogue opened.
    """
    if player.onebuffer >= 0 or state.interact != 0 or not confirm_pressed:
        return None
    if getattr(player, "disable_interaction_checks", False):
        # The GML sets interactedobject to -4 on a pressed frame when disabled.
        player.interactedobject = NOONE
        return None

    player.interactedobject = NOONE
    facing = state.facing
    d = int(state.darkzone)
    probe = mainchara_interaction_rectangle(player, facing, d, lookup=False)

    # The source first checks each type, then decides which *object type*
    # it will query again. A solid interactable wins if both overlap.
    chosen_type: Any | None = None
    for kind in (interactable_type, solid_type):
        found = collision_rectangle(
            probe.x1, probe.y1, probe.x2, probe.y2, kind, False, True
        )
        if _has_instance(found):
            chosen_type = kind

    if chosen_type is None:
        return None

    lookup = mainchara_interaction_rectangle(player, facing, d, lookup=True)
    target = collision_rectangle(
        lookup.x1, lookup.y1, lookup.x2, lookup.y2, chosen_type, False, True
    )
    if not _has_instance(target):
        return None

    player.interactedobject = target
    target.facing = (facing + 2) % 4
    # GML: with (interactedobject) scr_interact(). The default callback
    # initializes target.myinteract before invoking event_user(0).
    scr_interact(target)
    return target


__all__ = [
    "NOONE", "INTERACTABLE", "INTERACTABLE_SOLID",
    "FACING_DOWN", "FACING_RIGHT", "FACING_UP", "FACING_LEFT",
    "InteractionRect", "mainchara_interaction_rectangle",
    "mainchara_try_interact", "decrement_interaction_buffer",
    "mainchara_alarm_1", "user_event_0_adapter",
]
