"""Port of DELTARUNE's ``gml_GlobalScript_scr_getchar``.

Accepts the numeric character ID or GML's lowercase short/full aliases.
Adds to the first empty party slot (0, 1, or 2), without duplicate checks.
``state.getchar`` mirrors the original current-instance variable (1 if added,
0 if all three slots were occupied).
"""

from scr_losechar import _global_state, _refresh_darkcontrollers

_CHARACTER_IDS = {
    "kr": 1,
    "kris": 1,
    "su": 2,
    "susie": 2,
    "ra": 3,
    "ralsei": 3,
    "no": 4,
    "noelle": 4,
}


def scr_getchar(state, character):
    """Recruit a character, then refresh all existing dark controllers."""
    character_id = _CHARACTER_IDS.get(character, character) if isinstance(character, str) else character
    globals_ = _global_state(state)

    state.getchar = 0
    for party_slot in range(3):
        if globals_.char[party_slot] == 0:
            globals_.char[party_slot] = character_id
            state.getchar = 1
            break

    _refresh_darkcontrollers(state, globals_)
    # Like the original GML function, there is no explicit return statement.


__all__ = ["scr_getchar"]
