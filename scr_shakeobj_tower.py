"""Python port of ``gml_GlobalScript_scr_shakeobj_tower``.

Call from the instance that is requesting a shaking effect::

    scr_shakeobj_tower(state)
    scr_shakeobj_tower(state, target)
    scr_shakeobj_tower(state, target, shake_amount)
    scr_shakeobj_tower(state, target, shake_amount, shake_reduction)

``state`` supplies the GameMaker-compatible engine interface:

* ``id``, ``x``, ``y``: caller's ID and current position.
* ``instance_create(x, y, obj_type)``: create a shake-controller instance.
* ``i_ex(reference)`` (or ``instance_exists(reference)``): check a supplied
  target, but only when a target argument was given.
* ``obj_shakeobj_tower`` (optional): object resource. Its GML name is used if
  no resource attribute exists on ``state``.

The created object must provide ``event_user(0)``, OR the engine must provide
``state.event_user(created_instance, 0)``. This call is not optional: the GML
explicitly invokes User Event 0 after assigning the properties. The event's
actual shaking logic belongs to the yet-to-be-ported ``obj_shakeobj_tower``.

The GML function has no return statement; this port returns ``None`` as well.
The ``-1`` sentinel means 'do not override the shake object's own default'.
"""


def scr_shakeobj_tower(state, *args) -> None:
    """Spawn a tower shake controller for caller or a selected target.

    The 0-3 positional *args reproduce GML's ``argument_count`` branches:
    ``target``, ``shakeamt``, ``shakereduct``.
    """
    if len(args) > 3:
        raise TypeError(
            "scr_shakeobj_tower() accepts at most 3 GML arguments "
            "(target, shakeamt, shakereduct)"
        )

    shake_type = getattr(state, "obj_shakeobj_tower", "obj_shakeobj_tower")
    shake_obj = state.instance_create(state.x, state.y, shake_type)
    shake_obj.target = state.id

    if len(args) >= 1:
        checker = getattr(state, "i_ex", None)
        if not callable(checker):
            checker = state.instance_exists
        if checker(args[0]):
            shake_obj.target = args[0]

    if len(args) >= 2 and args[1] != -1:
        shake_obj.shakeamt = args[1]

    if len(args) >= 3 and args[2] != -1:
        shake_obj.shakereduct = args[2]

    # Corresponds to `with (_shakeobj) event_user(0);`.
    user_event = getattr(shake_obj, "event_user", None)
    if callable(user_event):
        user_event(0)
    else:
        engine_event = getattr(state, "event_user", None)
        if not callable(engine_event):
            raise AttributeError(
                "obj_shakeobj_tower must support event_user(0), or "
                "state must implement event_user(instance, 0)"
            )
        engine_event(shake_obj, 0)


__all__ = ["scr_shakeobj_tower"]
