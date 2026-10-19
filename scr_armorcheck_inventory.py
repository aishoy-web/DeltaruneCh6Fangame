"""Python port of gml_GlobalScript_scr_armorcheck_inventory.

Search the first 48 entries of global.armor (the unequipped armor inventory),
setting the calling instance's ``haveit`` and ``itemcount`` fields.

This does not inspect equipped armor (chararmor1/2/3) or depend on the
Chapter 6 optional third-armor-slot setting.
"""

from typing import Any


def scr_armorcheck_inventory(state: Any, armor_id: Any) -> int:
    """Find ``armor_id`` in the first 48 inventory slots.

    Returns 1 if any match exists, otherwise 0. Also sets ``state.itemcount``
    to the number of matching slots and resets both fields on every call.

    ``state`` can be the global state directly or a game/controller with a
    ``global_state`` attribute. The ``armor`` collection must support indices
    0 through 47, consistent with the original GML's fixed-length scan.
    """
    globals_ = getattr(state, "global_state", state)

    state.haveit = 0
    state.itemcount = 0

    # GML uses 'i' without 'var', so it is an instance variable as well.
    for i in range(48):
        state.i = i
        if globals_.armor[i] == armor_id:
            state.haveit = 1

        if globals_.armor[i] == armor_id:
            state.itemcount += 1

    state.i = 48
    return state.haveit
