"""Python port of ``gml_GlobalScript_c_walktoobject``.

Provides the six GML cutscene walking helpers. These functions *enqueue*
commands rather than moving instances immediately.

Required methods on ``state``:
    c_cmd(command, arg0, arg1, arg2, arg3)
    c_cmd_x(command, *args)
    c_wait(frame_count)

``c_walkto`` also delegates to ``state.c_walkdirect(x, y, frames)`` and,
when a facing direction is provided, ``state.c_delayfacing(delay, direction)``.
Their precise command formats are defined by the respective GML helpers and
should not be guessed here.

``c_walkto_actor`` needs an object with an ``actor_id`` sequence, provided as
``state.cutscene_master`` or ``state.obj_cutscene_master``. If the latter is an
object handle rather than a live instance, ``state.resolve_instance(handle)``
may resolve it.
"""


_MISSING = object()


def c_walktoobject(state, target, x_offset, y_offset, frames):
    """Queue a direct walk to target's position plus an (x, y) offset."""
    target_x = target.x + x_offset
    target_y = target.y + y_offset
    state.c_cmd("walkdirect", target_x, target_y, frames, 0)


def c_delaywalktoobject(state, delay, target, x_offset, y_offset, frames):
    """Queue a delayed direct walk to target's position plus an offset."""
    target_x = target.x + x_offset
    target_y = target.y + y_offset
    state.c_cmd_x("delaycmd", delay, "walkdirect", target_x, target_y, frames, 0)


def c_walktoobject_wait(state, target, x_offset, y_offset, frames):
    """Queue a direct walk and schedule a wait for the walk duration."""
    c_walktoobject(state, target, x_offset, y_offset, frames)
    state.c_wait(frames)


def c_delaywalktoobject_wait(state, delay, target, x_offset, y_offset, frames):
    """Queue a delayed walk, then wait for delay + movement duration."""
    c_delaywalktoobject(state, delay, target, x_offset, y_offset, frames)
    state.c_wait(delay + frames)


def _actor_ids(state):
    """Access the cutscene master's GML ``actor_id`` array."""
    master = getattr(state, "cutscene_master", None)
    if master is None:
        master = getattr(state, "obj_cutscene_master", None)
    if master is None:
        raise AttributeError("Cutscene master is required for c_walkto_actor")

    if not hasattr(master, "actor_id"):
        resolve = getattr(state, "resolve_instance", None)
        if callable(resolve):
            master = resolve(master)

    if master is None or not hasattr(master, "actor_id"):
        raise AttributeError("Cutscene master must expose an actor_id array")
    return master.actor_id


def c_walkto_actor(state, actor_slot, x_offset, y_offset, frames, facing=True):
    """Queue ``walkto`` with a cutscene actor mapping, if that slot exists.

    If ``actor_slot`` is beyond the actor array's length, forward it verbatim,
    matching the GML fallback. ``facing`` is forwarded twice by design.
    """
    actor_ids = _actor_ids(state)
    if len(actor_ids) > actor_slot:
        if actor_slot < 0:
            # Python indexes lists from the end; GML array lookup does not.
            raise IndexError("Negative cutscene actor slots are invalid")
        actor_obj = actor_ids[actor_slot]
    else:
        actor_obj = actor_slot
    state.c_cmd_x("walkto", actor_obj, x_offset, y_offset, frames, facing, facing)


def c_walkto_object(
    state,
    target,
    x_offset=0,
    y_offset=0,
    frames=_MISSING,
    facing=True,
):
    """Queue ``walkto`` using an object reference rather than an actor slot.

    GML declares the frame-count argument required despite the preceding two
    defaulted offsets. ``frames`` is likewise required here, even though Python
    syntax requires a sentinel to place it after defaulted parameters.
    The final command argument is always False, just as in the GML.
    """
    if frames is _MISSING:
        raise TypeError("c_walkto_object() missing required argument: 'frames'")
    state.c_cmd_x("walkto", target, x_offset, y_offset, frames, facing, False)


def c_walkto(state, target, frames, facing="none"):
    """Walk to target's *current* position; optionally queue delayed facing.

    Delegates to the separately-defined GML-derived ``c_walkdirect`` and
    ``c_delayfacing`` helpers so their actual semantics are preserved.
    """
    state.c_walkdirect(target.x, target.y, frames)
    if facing != "none":
        state.c_delayfacing(frames + 1, facing)


__all__ = [
    "c_walktoobject",
    "c_delaywalktoobject",
    "c_walktoobject_wait",
    "c_delaywalktoobject_wait",
    "c_walkto_actor",
    "c_walkto_object",
    "c_walkto",
]
