"""Python port of ``obj_plat_block_sinking``.

GameMaker inheritance:
    obj_plat_block_sinking -> obj_plat_movingplat -> obj_plat_floor

Supplied events:
    Create_0       inherited moving-platform Create, then sinking defaults
    Step_2         *own* End Step; does NOT call inherited End Step
    Other_4        Room Start; locate associated floortex and cache offsets

Begin Step and Draw are inherited from obj_plat_movingplat. ``movetype=0``
prevents scripted movement in the inherited Begin Step, though it still
increments ``t`` and snaps any registered riders. Sinking takes place in End
Step. This event does NOT recompute ``dif_x``/``dif_y``; the supplied GML does
not call ``event_inherited()`` there. No extra behavior has been invented.

The game engine must supply object lookup/collision and floortex-shift adapters.
The physics editor's Box2D controls are disabled: sprite-mask collision comes
from the engine, not this module's metadata.
"""
from __future__ import annotations

from typing import Any, Callable

from obj_plat_movingplat import PlatMovingPlat, movingplat_create

NOONE = -4


def _engine(instance: Any) -> Any:
    return getattr(instance, "engine", instance)


def _required_method(instance: Any, name: str):
    method = getattr(instance, name, None)
    if not callable(method):
        method = getattr(_engine(instance), name, None)
    if not callable(method):
        raise NotImplementedError(f"obj_plat_block_sinking requires {name}(...) on the object or engine")
    return method


def _exists(instance: Any, reference: Any) -> bool:
    if reference is None or reference == NOONE or reference == 0:
        return False
    checker = getattr(instance, "instance_exists", None)
    if not callable(checker):
        checker = getattr(_engine(instance), "instance_exists", None)
    if callable(checker):
        return bool(checker(reference))
    if isinstance(reference, (int, float, str)):
        raise NotImplementedError("numeric instance references require engine.instance_exists")
    return not getattr(reference, "destroyed", False)


def _resolve(instance: Any, reference: Any) -> Any:
    if not isinstance(reference, (int, float, str)):
        return reference
    return _required_method(instance, "resolve_instance")(reference)


def _resource(instance: Any, name: str) -> Any:
    return getattr(_engine(instance), name, name)


def _player_on_platform(instance: Any, player: Any) -> bool:
    """Match GameMaker ``_player.ground == id`` (integer IDs or Python refs)."""
    ground_ref = player.ground
    identity = getattr(instance, "id", instance)
    return ground_ref is instance or ground_ref == identity


def sinkingplat_create(instance: Any, *, parent_create: Callable | None = None) -> None:
    """Create_0: event_inherited(), then sinking-specific initialization."""
    movingplat_create(instance, parent_create=parent_create)
    instance.movetype = 0
    instance.sink = 0
    instance.sinkmax = 120
    instance.floortex = NOONE
    instance.visible = False


def sinkingplat_room_start(instance: Any) -> None:
    """Other_4: locate floortex at the platform's horizontal top edge."""
    collision_line = _required_method(instance, "collision_line")
    instance.floortex = collision_line(
        instance.x + 2,
        instance.y,
        instance.bbox_right - 2,
        instance.y,
        _resource(instance, "obj_plat_floortex_FLOOR"),
        False,
        True,
    )
    if _exists(instance, instance.floortex):
        floortex = _resolve(instance, instance.floortex)
        instance.floortex_x = floortex.x - instance.x
        instance.floortex_y = floortex.y - instance.y


def _transition_time(instance: Any) -> float:
    """Read the active obj_platswap's transition_time (no GML fallback)."""
    reference = getattr(_engine(instance), "obj_platswap", None)
    if reference is None:
        raise NotImplementedError(
            "sinking floortex shift requires the obj_platswap instance and transition_time"
        )
    if isinstance(reference, (int, float, str)):
        reference = _resolve(instance, reference)
    try:
        return reference.transition_time
    except AttributeError as exc:
        raise NotImplementedError(
            "obj_platswap must expose transition_time for sinking floortex shifts"
        ) from exc


def sinkingplat_end_step(instance: Any) -> None:
    """Step_2: sink under a standing player, then optionally shift floortex.

    **Do not call** movingplat_end_step: GML overrides End Step without an
    ``event_inherited()`` call. Pausing exits before *any* work, including
    floortex depth changes.
    """
    if getattr(instance, "destroyed", False):
        return
    globals_ = getattr(_engine(instance), "global_state", _engine(instance))
    if bool(getattr(globals_, "pause_plat", False)):
        return

    sinking = 0
    sink_xshake = 0
    player_ref = _required_method(instance, "instance_place")(
        instance.x, instance.y - 10, _resource(instance, "obj_plat_player")
    )
    if _exists(instance, player_ref):
        player = _resolve(instance, player_ref)
        if _player_on_platform(instance, player):
            if instance.sink < instance.sinkmax:
                instance.sink += 1
                sinking = 1
            instance.y = instance.ystart + instance.sink
            sink_xshake = (2 * (instance.sink % 2)) - 1

    if _exists(instance, instance.floortex):
        instance.depth = 999999
        if sinking and _transition_time(instance) <= 0:
            _required_method(instance, "scr_floortex_shift_objects")(
                instance.floortex, sink_xshake, 1
            )


class PlatBlockSinking(PlatMovingPlat):
    """Moving-platform subclass with GameMaker's sinking-block events."""

    object_name = "obj_plat_block_sinking"
    parent_object = "obj_plat_movingplat"
    sprite_index_default = "spr_plat_thinplat"
    visible_default = False
    solid_default = False
    persistent_default = False
    uses_physics = False
    is_sensor = False
    collision_shape = "box"

    def create(self, *, parent_create: Callable | None = None) -> None:
        sinkingplat_create(self, parent_create=parent_create)

    def end_step(self) -> None:
        sinkingplat_end_step(self)

    def room_start(self) -> None:
        sinkingplat_room_start(self)

    # begin_step and draw are inherited unchanged from PlatMovingPlat.


obj_plat_block_sinking = PlatBlockSinking

__all__ = [
    "PlatBlockSinking", "obj_plat_block_sinking",
    "sinkingplat_create", "sinkingplat_room_start", "sinkingplat_end_step",
]
