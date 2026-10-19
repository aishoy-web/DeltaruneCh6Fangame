"""Python port of DELTARUNE's ``gml_GlobalScript_scr_dead``.

The index is a *party slot*, matching the source GML's ``global`` arrays.
This helper only updates party/battle flags; it does not change HP, play
animations or sounds, or advance the active battle turn.

Pass the game/battle state, which may expose GML's global data through a
``global_state`` attribute. Otherwise the arrays are read from ``state``.
"""


def scr_dead(state, party_slot: int) -> None:
    """Mark the given party slot as downed, exactly as in the source GML."""
    global_state = getattr(state, "global_state", state)

    global_state.charmove[party_slot] = 0
    global_state.charcantarget[party_slot] = 0
    global_state.chardead[party_slot] = 1
    global_state.charaction[party_slot] = 0
    global_state.charspecial[party_slot] = 0


__all__ = ["scr_dead"]
