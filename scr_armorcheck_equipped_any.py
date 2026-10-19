"""Python port of gml_GlobalScript_scr_armorcheck_equipped_any.

Counts armor matches across ALL character indices of ``chararmor1``. The
number returned can exceed the number of characters because a character may
have the same armor in multiple slots.

The helper automatically uses ``scr_armorcheck_equipped`` from the companion
module, including its optional Chapter 6 third-slot support. A caller may
still supply ``armorcheck=`` or ``state.scr_armorcheck_equipped`` to override
its behavior.
"""

from typing import Any, Callable

from scr_armorcheck_equipped import scr_armorcheck_equipped


def scr_armorcheck_equipped_any(
    state: Any,
    armor_id: Any,
    *,
    armorcheck: Callable[[int, Any], int | bool] | None = None,
) -> int:
    """Return the total number of times ``armor_id`` is equipped."""
    globals_ = getattr(state, "global_state", state)

    if armorcheck is not None:
        check = armorcheck
    else:
        check = getattr(state, "scr_armorcheck_equipped", None)
        if not callable(check):
            check = lambda character_index, item_id: scr_armorcheck_equipped(
                state, character_index, item_id
            )

    total_wearing = 0
    for character_index in range(len(globals_.chararmor1)):
        total_wearing += check(character_index, armor_id)
    return total_wearing
