"""Port of ``gml_GlobalScript_scr_platmode_paused``.

Determine whether a platform-mode transition is currently pausing movement.

``state`` is the moving game instance (the GML ``self``). It must provide:

* ``i_ex(reference)`` or ``instance_exists(reference)`` to check existence;
* ``obj_platswap`` (optional; defaults to its GML name) identifying the
  platform-swap object;
* ``resolve_instance(reference)`` if ``obj_platswap`` is an object type/ID
  rather than an instance with a ``transition_time`` attribute;
* ``x``, ``y``, ``hspeed``, ``vspeed`` when undoing movement.

The helper only undoes position displacement. It does not alter the velocity,
stop the underlying movement system, or advance the platform swap transition.
"""


def scr_platmode_paused(state, undo_movement=True) -> bool:
    """Return True during an active platform swap; optionally undo movement.

    The source GML defaults to undoing the current step's ``hspeed`` and
    ``vspeed`` displacement while the platform-swap transition is active.
    """
    platswap_ref = getattr(state, "obj_platswap", "obj_platswap")

    exists = getattr(state, "i_ex", None)
    if not callable(exists):
        exists = state.instance_exists

    if not exists(platswap_ref):
        return False

    if hasattr(platswap_ref, "transition_time"):
        platswap = platswap_ref
    else:
        resolver = getattr(state, "resolve_instance", None)
        if not callable(resolver):
            raise AttributeError(
                "state.resolve_instance(reference) is required when "
                "obj_platswap is an object type or ID rather than an instance"
            )
        platswap = resolver(platswap_ref)
        if platswap is None:
            raise LookupError("obj_platswap exists but could not be resolved")

    if platswap.transition_time > 0:
        if undo_movement:
            state.x -= state.hspeed
            state.y -= state.vspeed
        return True

    return False


__all__ = ["scr_platmode_paused"]
