"""Python port of gml_GlobalScript_scr_armorcheck_equipped.

The original GML counts occurrences of an armor ID in a character's two
armor slots.  The Python port does the same by default.

Chapter 6 extension (opt-in): when ``global_state.armor_slot3_enabled`` is
True, also count ``global_state.chararmor3[character_index]``.  This does not
unlock the option, equip armor, modify stats, or save the setting; those are
separate responsibilities of the event, config menu, equipment manager and
save system.  No global.flag index has been assigned to this feature yet.
"""

from typing import Any


def scr_armorcheck_equipped(
    state: Any,
    character_index: int,
    armor_id: Any,
    *,
    include_third_slot: bool | None = None,
) -> int:
    """Return how many armor slots of a character contain ``armor_id``.

    Args:
        state: Global state or game context with a ``global_state`` attribute.
        character_index: Character index, not the active party slot.
        armor_id: Armor item ID to count.
        include_third_slot: Optional explicit override. If omitted, read
            ``global_state.armor_slot3_enabled`` (defaults to False).

    Raises:
        AttributeError: If the third slot is enabled but ``chararmor3`` has
            not been added to the global state yet.
        IndexError / KeyError: If a character index is missing from the
            arrays, as in the original index-based GML.
    """
    globals_ = getattr(state, "global_state", state)

    wearing = 0
    if globals_.chararmor1[character_index] == armor_id:
        wearing += 1
    if globals_.chararmor2[character_index] == armor_id:
        wearing += 1

    if include_third_slot is None:
        include_third_slot = bool(getattr(globals_, "armor_slot3_enabled", False))

    if include_third_slot:
        if not hasattr(globals_, "chararmor3"):
            raise AttributeError(
                "Third armor slot is enabled, but global_state.chararmor3 "
                "is not initialized."
            )
        if globals_.chararmor3[character_index] == armor_id:
            wearing += 1

    return wearing
