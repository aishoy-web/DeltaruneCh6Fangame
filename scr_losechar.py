"""Port of DELTARUNE's ``gml_GlobalScript_scr_losechar``.

GameMaker's ``global`` arrays live on ``state.global_state`` (or ``state``).
``with (obj_darkcontroller)`` is implemented using the optional engine adapter
``state.iter_instances(object_type)``. It may return zero or multiple instances.
``state.instances_of`` / ``state.get_instances`` and a ``darkcontrollers``
collection are also supported. If no controllers exist, the body of the
original GML ``with`` block does not execute.

The private ``_refresh_darkcontrollers`` helper is shared with ``scr_getchar``.
"""


def _global_state(state):
    return getattr(state, "global_state", state)


def _darkcontrollers(state):
    object_type = getattr(state, "obj_darkcontroller", "obj_darkcontroller")
    for method_name in ("iter_instances", "instances_of", "get_instances"):
        method = getattr(state, method_name, None)
        if callable(method):
            return method(object_type)
    # Convenience for simple Tkinter game engines without an instance registry.
    return getattr(state, "darkcontrollers", ()) or ()


def _refresh_darkcontrollers(state, global_state=None):
    """Rebuild each dark controller's party display from global.char[0:3].

    Preserves the original GML's subtle behavior: ``charpos`` entries for
    characters no longer present are *not* cleared, and ``faceaction`` is
    only reset when at least one dark controller exists.
    """
    globals_ = _global_state(state) if global_state is None else global_state
    for controller in _darkcontrollers(state):
        controller.chartotal = 0
        for index in range(4):
            controller.havechar[index] = 0

        for party_slot in range(3):
            globals_.faceaction[party_slot] = 0
            character_id = globals_.char[party_slot]
            if character_id != 0:
                controller.chartotal += 1
            if character_id in (1, 2, 3, 4):
                character_index = character_id - 1
                controller.havechar[character_index] = 1
                controller.charpos[character_index] = party_slot


def scr_losechar(state) -> None:
    """Remove companion slots 1 and 2 and reset party-related menus."""
    globals_ = _global_state(state)
    globals_.char[2] = 0
    globals_.char[1] = 0

    _refresh_darkcontrollers(state, globals_)

    globals_.submenu = 0
    globals_.charselect = -1
    for i in range(36):
        globals_.submenucoord[i] = 0


__all__ = ["scr_losechar"]
