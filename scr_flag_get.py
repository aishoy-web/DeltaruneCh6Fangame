"""Python port of DELTARUNE's ``gml_GlobalScript_scr_flag_get``.

``state.flag`` and ``state.flagname`` represent GameMaker's corresponding
``global`` arrays. They are owned by the game's persistent state/save system.

``scr_flag_get_ext`` now uses ``scr_get_bitmask_value`` directly. The optional
``bitmask_getter`` argument is retained to support existing callers/tests.
"""

from scr_bitmask import scr_get_bitmask_value


def scr_flag_get(state, flag_index):
    """Return ``global.flag[arg0]``."""
    return state.flag[flag_index]


def scr_flag_name_get(state, flag_index):
    """Return the flag name, or ``'*unknown flag*'`` for undefined entries."""
    try:
        value = state.flagname[flag_index]
    except (IndexError, KeyError):
        return "*unknown flag*"
    return "*unknown flag*" if value is None else value


def scr_flag_get_ext(
    state,
    flag_index,
    bit_index,
    bit_count=1,
    *,
    bitmask_getter=None,
):
    """Read a packed value from a global flag.

    A negative bit index follows the supplied GML literally: call
    ``scr_flag_get`` but do not return its result (Python returns ``None``).
    """
    if bit_index < 0:
        scr_flag_get(state, flag_index)
        return None

    getter = bitmask_getter if bitmask_getter is not None else scr_get_bitmask_value
    return getter(state.flag[flag_index], bit_index, bit_count)
