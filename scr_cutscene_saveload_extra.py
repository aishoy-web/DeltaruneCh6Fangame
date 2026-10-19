"""Python port of ``gml_GlobalScript_scr_cutscene_saveload_extra``.

Functions:
    scr_cutscene_save_objects(state, *objects)
    scr_cutscene_save_song(state, save_position=False)
    scr_cutscene_save_music(state, cutscene=None)
    scr_cutscene_load_music(state, cutscene=None)

``state`` is the game/engine context. GameMaker's ``global`` variables are
expected on ``state.global_state`` (or directly on ``state``). This is the
same convention used by this project's other standalone GML ports.

The first two functions reproduce ``with (obj_cutscene_master)`` by iterating
``state.iter_instances(state.obj_cutscene_master)``. For simpler engines, the
``state.cutscene_masters`` collection or the instance itself can be used.

The music save/load functions run in the calling cutscene's scope in GML,
not inside a ``with`` block. By default, they use ``state`` as the cutscene
instance; when working from the game object, specify ``cutscene=master``.
They read ``state.global_state.currentsong`` and call these game adapters:

    snd_is_playing(sound_instance)
    audio_sound_get_pitch(sound_instance)
    audio_sound_get_gain(sound_instance)
    audio_sound_get_track_position(sound_instance)
    snd_stop(sound_instance)
    snd_init(track_id) -> track_id or active resource ID
    mus_loop(sound_instance) -> newly playing sound_instance
    snd_pitch(sound_instance, pitch)
    snd_volume(sound_instance, volume, duration)
    audio_sound_set_track_position(sound_instance, seconds)
    audio_resume_sound(sound_instance)
    snd_pause(sound_instance)

``snd_init`` may need to update ``global_state.currentsong[1]`` as a side
 effect, just as the original GML implicitly assumes. This module does not
invent a music-player implementation or perform file persistence.

Intentional source details:
* ``scr_cutscene_save_objects`` only works when ``scr_debug()`` is true.
* The saved-object array has at most 10 slots; 99999999, -4 and None (as
  GML ``undefined``) are treated as the first free slot.
* ``save_position=False`` disables restoring a prior track position.
* Loading a resumed track corrects the source's apparent ``cuurrentsong``
  typo to ``currentsong`` so resume is functional.
"""

from __future__ import annotations

import logging
from typing import Any


_EMPTY_OBJECT_MARKERS = (99999999, -4, None)
_MAX_SAVED_OBJECTS = 10


def _globals(state: Any) -> Any:
    return getattr(state, "global_state", state)


def _masters(state: Any):
    """Yield cutscene masters just as ``with (obj_cutscene_master)`` does."""
    object_type = getattr(state, "obj_cutscene_master", "obj_cutscene_master")
    for method_name in ("iter_instances", "instances_of", "get_instances"):
        getter = getattr(state, method_name, None)
        if callable(getter):
            yield from getter(object_type)
            return

    masters = getattr(state, "cutscene_masters", None)
    if masters is not None:
        yield from masters
    elif hasattr(state, "save_object") or hasattr(state, "save_mus"):
        # Allow a direct call on a cutscene master in a lightweight engine.
        yield state


def _debug_message(state: Any, message: str) -> None:
    output = getattr(state, "show_debug_message", None)
    if callable(output):
        output(message)
    else:
        logging.debug("%s", message)


def _debug_print(state: Any, message: str) -> None:
    output = getattr(state, "scr_debug_print", None)
    if callable(output):
        output(message)
    else:
        logging.warning("%s", message)


def _debug_enabled(state: Any) -> bool:
    checker = getattr(state, "scr_debug", None)
    if callable(checker):
        return bool(checker())
    # A straightforward fallback for engines without the GML scr_debug script.
    return bool(getattr(state, "debug", False))


def scr_cutscene_save_objects(state: Any, *objects: Any) -> None:
    """Append up to ten object references to each cutscene master's slots.

    Matching GML, the operation is entirely disabled outside debug mode.
    The source stops scanning at the first sentinel/undefined entry; it
    doesn't search for holes farther into the list.
    """
    if not _debug_enabled(state):
        return

    for master in _masters(state):
        saved = master.save_object
        # Uninitialized GML indices evaluate to ``undefined``. Pad a short
        # Python list with None to match that behavior.
        if len(saved) < _MAX_SAVED_OBJECTS:
            saved.extend([None] * (_MAX_SAVED_OBJECTS - len(saved)))

        start_slot = 0
        for index in range(_MAX_SAVED_OBJECTS):
            value = saved[index]
            if value is None or value == 99999999 or value == -4:
                _debug_message(state, "we breakin out of here")
                break
            start_slot += 1

        for index, obj in enumerate(objects):
            slot = start_slot + index
            if slot >= _MAX_SAVED_OBJECTS:
                _debug_print(state, "Cutscene object limit reached.")
                break
            saved[slot] = obj


def scr_cutscene_save_song(state: Any, save_position: bool = False) -> None:
    """Mark each cutscene master as needing to save its current music.

    ``save_position=True`` keeps a previously requested position save;
    otherwise it initializes ``save_mus_pos`` to 0, enabling capture when
    ``scr_cutscene_save_music`` runs. ``False`` disables position capture.
    """
    for master in _masters(state):
        master.save_mus = True
        if save_position:
            position = getattr(master, "save_mus_pos", None)
            if position is None or position < 0:
                master.save_mus_pos = 0
        else:
            master.save_mus_pos = -1


def scr_cutscene_save_music(state: Any, cutscene: Any = None) -> None:
    """Snapshot the current audio state into the calling cutscene instance."""
    master = state if cutscene is None else cutscene
    if not getattr(master, "save_mus", False):
        return

    current_song = _globals(state).currentsong
    if current_song[1] == -4:
        master.save_mus_track = -4
        master.save_mus_playing = False
        master.save_mus_vol = 1
        master.save_mus_pitch = 1
        master.save_mus_pos = -1
    else:
        sound_instance = current_song[1]
        master.save_mus_track = current_song[0]
        master.save_mus_playing = state.snd_is_playing(sound_instance)
        master.save_mus_pitch = state.audio_sound_get_pitch(sound_instance)
        master.save_mus_vol = state.audio_sound_get_gain(sound_instance)

        position = getattr(master, "save_mus_pos", None)
        if position is not None and position >= 0:
            master.save_mus_pos = state.audio_sound_get_track_position(
                sound_instance
            )
        else:
            master.save_mus_pos = -1


def scr_cutscene_load_music(state: Any, cutscene: Any = None) -> None:
    """Restore previously captured audio state into the game music player."""
    master = state if cutscene is None else cutscene
    if not getattr(master, "save_mus", False):
        return

    current_song = _globals(state).currentsong

    if current_song[0] != master.save_mus_track:
        if current_song[0] != -4:
            state.snd_stop(current_song[1])

        if master.save_mus_track != -4:
            # Preserve GML call order. The sound system may update
            # currentsong[1] during snd_init() before mus_loop() uses it.
            current_song[0] = state.snd_init(master.save_mus_track)
            current_song[1] = state.mus_loop(current_song[1])
        else:
            current_song[0] = -4
            current_song[1] = -4

    if master.save_mus_track != -4:
        sound_instance = current_song[1]
        state.snd_pitch(sound_instance, master.save_mus_pitch)
        state.snd_volume(sound_instance, master.save_mus_vol, 0)

        if master.save_mus_pos >= 0:
            state.audio_sound_set_track_position(
                sound_instance, master.save_mus_pos
            )

        if state.snd_is_playing(sound_instance) != master.save_mus_playing:
            if master.save_mus_playing:
                # Supplied GML spells this ``global.cuurrentsong[1]``;
                # using currentsong fixes that apparent typo.
                state.audio_resume_sound(sound_instance)
            else:
                state.snd_pause(sound_instance)


__all__ = [
    "scr_cutscene_save_objects",
    "scr_cutscene_save_song",
    "scr_cutscene_save_music",
    "scr_cutscene_load_music",
]
