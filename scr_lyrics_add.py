"""Python port of DELTARUNE's ``gml_GlobalScript_scr_lyrics_add``.

The caller (typically a lyrics/chart controller) owns four attributes:
``lyric_time``, ``lyrics``, ``timed_lyrics``, and ``lyric_count``.

Lists expand automatically when an entry is added, mirroring GameMaker's
indexed-array assignments. Preallocated mutable arrays are also supported.
"""


# Characters removed from the displayed lyric when no separate timed lyric
# was supplied. Order and exact characters match the source GML.
_LYRIC_MARKERS = ("-", "<", ">", "＜", "＞", "+", "＋")


def _set_at(array, index, value):
    """Assign an indexed entry, extending Python lists like GML arrays."""
    if isinstance(array, list) and index >= len(array):
        array.extend([None] * (index + 1 - len(array)))
    array[index] = value


def scr_lyrics_add(state, time, text, timed_text="") -> None:
    """Add a lyric entry at ``state.lyric_count``.

    If ``timed_text`` is the empty string, store the original ``text`` as the
    timed lyric and strip the seven markup characters from the display lyric.
    If a nonempty ``timed_text`` is supplied, preserve both strings unchanged.

    This function changes the controller in place and does not draw lyrics.
    """
    if timed_text == "":
        timed_text = text
        for marker in _LYRIC_MARKERS:
            text = text.replace(marker, "")

    index = state.lyric_count
    _set_at(state.lyric_time, index, time)
    _set_at(state.lyrics, index, text)
    _set_at(state.timed_lyrics, index, timed_text)
    state.lyric_count += 1
