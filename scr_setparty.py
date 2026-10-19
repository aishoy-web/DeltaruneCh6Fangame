"""Python port of ``gml_GlobalScript_scr_setparty``.

The source contains two public functions:

* ``scr_setparty`` locates Kris using ``obj_mainchara``.
* ``setparty`` locates Kris using the hard-coded numeric reference ``1200``.

Both first clear the existing party/followers, then recruit selected character
IDs 2, 3, and/or 4. Follower instances are only created when Kris exists.

Engine adapter required on ``state``:
    safe_delete(object_type)          delete previous follower instances
    i_ex(reference) -> bool           GameMaker-style instance existence check
    resolve_instance(reference)       find live instance by object or numeric GML reference
    instance_create(x, y, obj_type)   create followers (when no custom method exists)

The port now imports ``scr_losechar``, ``scr_getchar`` and
``scr_makecaterpillar`` directly. Existing ``state.scr_*`` methods remain
supported for compatibility, but are no longer required. The imported modules
expect ``state.iter_instances(obj_darkcontroller)`` for dark-controller updates.

``instance_exists(reference)`` is accepted in place of ``i_ex``. When the
supplied ``obj_mainchara`` value already is an instance (with x/y), it can
be used directly without ``resolve_instance``.

``state.global_state.darkzone`` (or ``state.darkzone``) selects the Light World
(0) or Dark World (nonzero) follower offsets. Object names default to their
GML string names if no matching asset handles are present on ``state``.

These helpers change party data and follower instances but do not themselves
serialize save data or draw any sprites. Hook their engine methods into the
existing game architecture.
"""


from scr_losechar import scr_losechar
from scr_getchar import scr_getchar
from scr_makecaterpillar import scr_makecaterpillar


def _call_script(state, method_name, fallback, *args):
    """Prefer an existing engine method; otherwise use our standalone port."""
    method = getattr(state, method_name, None)
    if callable(method):
        return method(*args)
    return fallback(state, *args)


def _has_instance(state, reference) -> bool:
    checker = getattr(state, "i_ex", None)
    if checker is None:
        checker = state.instance_exists
    return bool(checker(reference))


def _resolve_kris(state, reference):
    if hasattr(reference, "x") and hasattr(reference, "y"):
        return reference
    resolver = getattr(state, "resolve_instance", None)
    if not callable(resolver):
        raise AttributeError(
            "When Kris exists, state must implement resolve_instance(reference) "
            "for object handles and instance IDs."
        )
    kris = resolver(reference)
    if kris is None:
        raise LookupError(f"Kris exists but could not resolve instance {reference!r}")
    return kris


def _setparty(state, kris_ref, char2, char3, char4) -> None:
    # GML checks Kris before it modifies the party.
    make_followers = _has_instance(state, kris_ref)

    # These two operations always run, even if no character is requested or
    # Kris has not been instantiated in the current room.
    _call_script(state, "scr_losechar", scr_losechar)
    follower_type = getattr(state, "obj_caterpillarchara", "obj_caterpillarchara")
    state.safe_delete(follower_type)

    global_state = getattr(state, "global_state", state)
    # Only required when an actual follower will be created.
    darkzone = None
    kris = None
    slot = 0

    for enabled, character_id in ((char2, 2), (char3, 3), (char4, 4)):
        # Matches the source's `argN == true`, not generic truthiness.
        if enabled != True:
            continue

        _call_script(state, "scr_getchar", scr_getchar, character_id)

        if make_followers:
            if kris is None:
                kris = _resolve_kris(state, kris_ref)
                darkzone = global_state.darkzone

            if character_id == 2:
                halign, valign = (3, 6) if darkzone == 0 else (6, 16)
            elif character_id == 3:
                halign, valign = 2, 12
            else:
                halign, valign = (2, 9) if darkzone == 0 else (4, 18)

            follower = _call_script(
                state, "scr_makecaterpillar", scr_makecaterpillar,
                kris.x, kris.y, character_id, slot,
            )
            follower.halign = halign
            follower.valign = valign
            follower.x -= halign
            follower.y -= valign

        # Slots advance even when no follower is created.
        slot += 1


def scr_setparty(state, char2=False, char3=False, char4=False) -> None:
    """Set party members; find Kris via the ``obj_mainchara`` object type."""
    kris_ref = getattr(state, "obj_mainchara", "obj_mainchara")
    _setparty(state, kris_ref, char2, char3, char4)


def setparty(state, char2=False, char3=False, char4=False) -> None:
    """Legacy variant of ``scr_setparty``, using the literal GML Kris reference ``1200``."""
    _setparty(state, 1200, char2, char3, char4)


__all__ = ["scr_setparty", "setparty"]
