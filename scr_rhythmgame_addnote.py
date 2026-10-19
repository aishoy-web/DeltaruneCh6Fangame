"""Python port of DELTARUNE's ``scr_rhythmgame_addnote`` script.

This module contains all four GML functions from the script:

* scr_rhythmgame_addnote
* scr_rhythmgame_addnote_range
* scr_rhythmgame_addnote_bpm
* scr_rhythmgame_addnote_snap

Each function receives ``state`` as its first argument, representing the GML
instance that owns the note arrays and ``maxnote``. Arrays may be ordinary Python
lists (automatically expanded like GML arrays) or preallocated mutable/indexable
collections. Initialize the six arrays and ``maxnote`` in your rhythm-game
controller's setup code.

These ports deliberately keep the supplied GML behavior, including the unused
``arg4`` parameter and the unusual BPM/snap calculations described below.
"""


def _set_at(array, index, value):
    """Write an indexed field, growing Python lists as needed for GML parity."""
    if isinstance(array, list) and index >= len(array):
        array.extend([None] * (index + 1 - len(array)))
    array[index] = value


def scr_rhythmgame_addnote(
    state,
    note_time,
    note_type,
    note_end=0,
    note_anim=0,
    arg4=False,
) -> None:
    """Append one note at ``state.maxnote`` and mark it active/unscored.

    ``arg4`` is accepted for signature compatibility; the original GML ignores it.
    """
    index = state.maxnote
    _set_at(state.notetime, index, note_time)
    _set_at(state.notetype, index, note_type)
    _set_at(state.noteend, index, note_end)
    _set_at(state.noteanim, index, note_anim)
    _set_at(state.notealive, index, 1)
    _set_at(state.notescore, index, 0)
    state.maxnote += 1


def scr_rhythmgame_addnote_range(
    state,
    note_time,
    note_type,
    note_end=0,
    note_anim=0,
    arg4=False,
) -> None:
    """Add a note in the chart range or as a pre-scored previous-loop note.

    When ``chart_end == 0``, all notes are added normally. When a chart range is
    set, notes in its prior-track-length interval are added inactive with a
    score of 40; notes outside both valid intervals are skipped entirely.
    """
    if (
        state.chart_end == 0
        or (
            note_time < state.chart_end - state.track_length
            and note_time >= state.chart_start - state.track_length
        )
    ):
        scr_rhythmgame_addnote(
            state, note_time, note_type, note_end, note_anim, arg4
        )

        if state.chart_end > 0:
            index = state.maxnote - 1
            _set_at(state.notealive, index, 0)
            _set_at(state.notescore, index, 40)
        return

    if (
        (note_time < state.chart_start or note_time > state.chart_end)
        and state.chart_end > 0
    ):
        return

    scr_rhythmgame_addnote(
        state, note_time, note_type, note_end, note_anim, arg4
    )


def scr_rhythmgame_addnote_bpm(
    state,
    note_time,
    note_type,
    note_end=0,
) -> None:
    """Convert a beat/meter-based note to chart time and add it.

    Fidelity note: The supplied GML subtracts ``startoffset`` *twice* from
    ``note_time`` when ``note_end != 0``. This port intentionally retains it.
    """
    note_time *= state.meter
    note_time -= state.startoffset

    if note_end != 0:
        note_end *= state.meter
        note_time -= state.startoffset  # Faithful to the supplied GML.

    scr_rhythmgame_addnote(state, note_time, note_type, note_end)


def scr_rhythmgame_addnote_snap(
    state,
    note_time,
    note_type,
    note_end=0,
    subdivisions=16,
) -> None:
    """Snap a note to meter subdivisions, matching the supplied GML exactly.

    Fidelity notes:
      * GML's round() uses ties-to-even rounding, as Python's round() does.
      * The source calculates ``note_end`` when nonzero but then writes
        ``subdivisions`` into the noteend array instead. Preserved here.
    """
    note_time = (note_time / state.meter) * subdivisions
    note_time = (round(note_time) / subdivisions) * state.meter

    if note_end != 0:
        note_end = (note_time / state.meter) * subdivisions
        note_end = (round(note_time) / subdivisions) * state.meter

    # The original source uses arg3 (subdivisions), NOT arg2 (note_end).
    scr_rhythmgame_addnote(state, note_time, note_type, subdivisions)
