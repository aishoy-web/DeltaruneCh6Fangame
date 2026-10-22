"""Chapter 6 room-controller *framework* derived from obj_room_torhouse.

This is intentionally NOT a port of Chapter 5's narrative content. It preserves
basic inspectable positions/identifiers and the room-controller event interface,
but leaves story-specific visuals, NPCs, plot gating, and dialogue to callbacks.

NOT included by default:
  - obj_ch5_LW02 cutscene
  - Chapter 5 weird-route / sideb redirection
  - Chairiel, toast, toaster, and broken-TV variants
  - Chapter 5 dialogue strings and chapter-specific plot thresholds

Source reference: user-supplied obj_room_torhouse GML Create/Alarm/Step.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from room_controller import DialogueHandler, ReadablePoint, RoomController


TORHOUSE_READABLES = (
    ReadablePoint("torhouse_fridge", 200, 128, 1.4, 1.2),
    ReadablePoint("torhouse_sink", 232, 116, 1.6, 1.0),
    ReadablePoint("torhouse_stovetop", 272, 116, 1.4, 1.0),
    ReadablePoint("torhouse_phone", 376, 140),
    ReadablePoint("torhouse_books", 577, 189),
    ReadablePoint("torhouse_trash", 344, 136),
    ReadablePoint("torhouse_tv_stand", 480, 132, 1.6, 1.0),
)

# Analysis-only mapping from the GML. Not required for new string-key dispatch.
# The special Chapter 5 routes are documented, not enabled by default.
LEGACY_CON = {
    "torhouse_fridge": 10,
    "torhouse_sink": 20,
    "torhouse_phone": 30,
    "torhouse_tv": 40,
    "torhouse_tv_stand": 45,
    "torhouse_stovetop": 50,
    "torhouse_books": 60,
    "torhouse_trash": 70,
    "torhouse_weird": 80,
    "w_torhouse_chairiel": 90,
}


class TorhouseRoomController(RoomController):
    """Room-local controller for Toriel's House, designed for Chapter 6.

    To show dialogue, install a handler keyed by `extflag` (for example,
    `torhouse_fridge`). A handler should use the *existing* game dialogue API.

    Optional scene_setup(controller) controls Chapter 6 plot-state variants.
    Use game.global_state.plot / flag in that callback, rather than copying
    Chapter 5's `global.plot >= 5` or weird-route logic.
    """

    object_name = "obj_room_torhouse"
    sprite_index = "spr_event"
    visible = False
    solid = False
    persistent = False
    uses_physics = False
    collision_shape = "box"  # Disabled physics metadata from editor.

    def __init__(
        self,
        game: Any,
        *,
        handlers: Mapping[str, DialogueHandler] | None = None,
        dialogue_active: Callable[[], bool] | None = None,
        scene_setup: Callable[["TorhouseRoomController"], None] | None = None,
        scene_step: Callable[["TorhouseRoomController"], None] | None = None,
    ) -> None:
        super().__init__(
            game,
            room_id="torhouse",
            readables=TORHOUSE_READABLES,
            handlers=handlers,
            dialogue_active=dialogue_active,
            on_create=scene_setup,
            on_step=scene_step,
        )


obj_room_torhouse = TorhouseRoomController

__all__ = [
    "TORHOUSE_READABLES", "LEGACY_CON",
    "TorhouseRoomController", "obj_room_torhouse",
]
