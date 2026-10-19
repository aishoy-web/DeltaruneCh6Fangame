"""Python port of gml_GlobalScript_scr_armorcheck_equipped_party.

Count copies of an armor item equipped by the three *active party slots*.
Unlike scr_armorcheck_equipped_any, this looks at global.char[0:3] and
uses the character ID in each occupied slot to look up equipment.

The imported scr_armorcheck_equipped preserves GameMaker's two armor slots
by default; when the Chapter 6 optional third armor slot is enabled in the
global state, it also counts chararmor3. The party-counting function itself
needs no special-case logic for that feature.
"""

from typing import Any, Callable

from scr_armorcheck_equipped import scr_armorcheck_equipped


def scr_armorcheck_equipped_party(
    state: Any,
    armor_id: Any,
    *,
    armorcheck: Callable[[int, Any], int | bool] | None = None,
) -> int:
    """Count occurrences of ``armor_id`` equipped by current party members.

    Iterates exactly the three original GML party slots (indices 0, 1, 2),
    skips empty slots (character ID 0), and sums the individual character's
    armor matches. Multiple copies on one character contribute separately.

    Args:
        state: Global state, or game context with a ``global_state`` attribute.
        armor_id: Armor item ID to count.
        armorcheck: Optional `(character_id, armor_id) -> count` override,
            useful for testing or adapting to a custom equipment system.

    Returns:
        Total matches across the currently active party (0 or greater).
    """
    globals_ = getattr(state, "global_state", state)

    if armorcheck is not None:
        check = armorcheck
    else:
        check = getattr(state, "scr_armorcheck_equipped", None)
        if not callable(check):
            check = lambda character_id, item_id: scr_armorcheck_equipped(
                state, character_id, item_id
            )

    total_wearing = 0
    for party_slot in range(3):
        character_id = globals_.char[party_slot]
        if character_id != 0:
            total_wearing += check(character_id, armor_id)

    return total_wearing
