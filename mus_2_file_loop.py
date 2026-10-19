"""Python port of ``gml_GlobalScript_mus_2_file_loop``.

Plays an intro music file, then creates/configures a persistent
``obj_setup_music_loop_track`` instance that the engine will use to
transition to the loop file.

Required engine adapters on ``state``:
    mus_play_ext(track, loops, volume, pitch) -> playing_sound_instance
    instance_create(x, y, object_type) -> mutable setup instance
    snd_init(track) -> initialized loop-track resource

``state.global_state.currentsong`` (or ``state.currentsong``) must be a
mutable collection with at least two elements:
    [0]: current track resource / track ID
    [1]: playing sound-instance reference

The engine must implement the setup object's actual intro-to-loop behavior;
this function only initializes that object, as the original GML does.
"""

from typing import Any


def mus_2_file_loop(
    state: Any,
    intro_name: Any,
    loop_name: Any,
    volume: float,
    pitch: float,
) -> None:
    """Begin intro playback and configure a persistent loop-track controller.

    Preserves the original order of operations, including ``loops=-1``,
    recording ``currentsong[0]`` (not ``currentsong[1]``) as ``introtrack``,
    and leaving ``currentsong[0]`` untouched by this helper itself.
    """
    global_state = getattr(state, "global_state", state)

    global_state.currentsong[1] = state.mus_play_ext(
        intro_name, -1, volume, pitch
    )

    setup_type = getattr(
        state,
        "obj_setup_music_loop_track",
        "obj_setup_music_loop_track",
    )
    controller = state.instance_create(0, 0, setup_type)
    controller.persistent = True
    controller.volume = volume
    controller.pitch = pitch
    controller.introtrack = global_state.currentsong[0]
    controller.looptrack = state.snd_init(loop_name)
    controller.introname = intro_name
    controller.loopname = loop_name


__all__ = ["mus_2_file_loop"]
