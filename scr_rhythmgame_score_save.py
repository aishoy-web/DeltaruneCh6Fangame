"""Python port of DELTARUNE's ``scr_rhythmgame_score_save``.

``state.flag`` represents GameMaker's ``global.flag`` and must be an
indexable, mutable collection (typically a list or dictionary). Its score
slots should be initialized by the game's global/save-data setup.

``scr_rhythmgame_song_flag`` is imported from the companion module.
The optional ``song_flag`` callback remains supported for testing or overrides.

This function changes in-memory score flags. Persisting those flags to a save
file is the responsibility of the game's existing save system.
"""


from scr_rhythmgame_song_flag import scr_rhythmgame_song_flag


def scr_rhythmgame_score_save(
    state,
    song_id,
    score,
    variant=False,
    flag_index=0,
    only_if_higher=True,
    *,
    song_flag=None,
) -> None:
    """Store a rhythm-game score in ``state.flag``.

    Args:
        state: Object holding the GameMaker-equivalent ``flag`` collection.
        song_id: Original GML ``arg0`` (song identifier).
        score: Original GML ``arg1`` (score to store).
        variant: Original GML ``arg2`` (passed to song-flag lookup).
        flag_index: Original GML ``arg3``; 0 requests song-flag lookup.
        only_if_higher: Original GML ``arg4``. If True (the default), only
            save scores greater than or equal to the current score. If False,
            overwrite unconditionally.
        song_flag: Optional custom flag-lookup callable. If omitted, uses
            ``scr_rhythmgame_song_flag`` automatically.

    Returns:
        None, matching the original GML script.
    """
    if flag_index == 0:
        lookup = song_flag if song_flag is not None else scr_rhythmgame_song_flag
        flag_index = lookup(song_id, variant)

    if not only_if_higher or score >= state.flag[flag_index]:
        state.flag[flag_index] = score
