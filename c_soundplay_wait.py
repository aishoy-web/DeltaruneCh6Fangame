"""Python port of DELTARUNE's ``gml_GlobalScript_c_soundplay_wait``.

The two functions are cutscene scripting helpers. They enqueue a soundplay
command, followed by a wait measured in game frames. They do NOT sleep or
play audio themselves.

``state`` is the cutscene/script controller exposing:

* ``c_cmd(command_name, arg0, arg1, arg2, arg3)``
* ``c_wait(frame_count)``
* ``audio_sound_length(sound_id) -> seconds``
* ``room_speed`` (game steps/second)

Adapt these operations to the existing cutscene system when integrating.
"""

from math import ceil, floor


def _gml_round(value: float) -> int:
    """Round to the nearest integer with halves away from zero, as GML does."""
    return floor(value + 0.5) if value >= 0 else ceil(value - 0.5)


def c_soundplay_wait(state, sound_id) -> None:
    """Queue sound playback and a wait for the sound's length in frames.

    Equivalent to GML:
        c_cmd("soundplay", arg0, 0, 0, 0);
        c_wait(round(audio_sound_length(arg0) * room_speed));
    """
    state.c_cmd("soundplay", sound_id, 0, 0, 0)
    frames = _gml_round(state.audio_sound_length(sound_id) * state.room_speed)
    state.c_wait(frames)


def c_playsound_wait(state, sound_id) -> None:
    """Alias for ``c_soundplay_wait``, matching the original GML."""
    c_soundplay_wait(state, sound_id)
