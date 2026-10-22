"""Small, engine-adapter-based controller for GameMaker-style room-controller objects.

A room resource (map/layout) is NOT a room controller (a placed GameMaker object).
The room manager is responsible for loading visual/collision room data and dispatching
Create/Step; this class handles room-specific interactions and story hooks.

Engine contract (supplied by the real game, not invented here):
    game.instance_create(x, y, 'obj_readable_room1') -> instance
    game.global_state.interact -> integer (shared interaction lock)
    dialogue_active() -> bool (adapter for the game's actual dialogue manager)

The room-specific interaction callbacks must start their own dialogue using the
actual dialogue system; this module does not implement DialogueBox or d_make().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class ReadablePoint:
    """Room-local inspection point, corresponding to obj_readable_room1."""

    extflag: str
    x: float
    y: float
    xscale: float = 1.0
    yscale: float = 1.0


# Receives the controller plus the number of previous conversations.
DialogueHandler = Callable[["RoomController", int], None]
CreateHook = Callable[["RoomController"], None]


class RoomController:
    """Reusable room interaction lifecycle, independent of story dialogue text.

    Provide a dialogue_active adapter and one handler for each interactive key.
    When a handler launches a dialogue, the controller owns the global interaction
    lock until the dialogue is no longer active. A delayed dialogue manager can
    keep dialogue_active() true while queuing/typing text.

    Unlike the original GML, unknown/unimplemented interaction IDs are rejected
    rather than leaving the controller stuck in an unhandled `con` state.
    """

    def __init__(
        self,
        game: Any,
        *,
        room_id: str,
        readables: Sequence[ReadablePoint] = (),
        handlers: Mapping[str, DialogueHandler] | None = None,
        dialogue_active: Callable[[], bool] | None = None,
        on_create: CreateHook | None = None,
        on_step: CreateHook | None = None,
    ) -> None:
        self.game = game
        self.room_id = room_id
        self.readables = tuple(readables)
        self.handlers: dict[str, DialogueHandler] = dict(handlers or {})
        self._dialogue_active_adapter = dialogue_active
        self.on_create = on_create
        self.on_step = on_step
        self.created = False
        self.spawned_readables: list[Any] = []
        self.pending: tuple[str, int] | None = None
        self.active_interaction: str | None = None
        self._owns_interact_lock = False
        self.con = -1  # Compatibility field; new dispatch uses string IDs.
        self._times_talked = 0
        self.npc_animate = False
        self.npc_animate_target = -4

    def _globals(self) -> Any:
        global_state = getattr(self.game, "global_state", None)
        if global_state is None:
            raise NotImplementedError(
                "RoomController requires game.global_state with an 'interact' field"
            )
        return global_state

    def _dialogue_active(self) -> bool:
        if self._dialogue_active_adapter is not None:
            return bool(self._dialogue_active_adapter())
        callback = getattr(self.game, "d_ex", None)
        if callable(callback):
            return bool(callback())
        raise NotImplementedError(
            "RoomController requires dialogue_active() or a game.d_ex() adapter"
        )

    def create(self) -> None:
        """Room-controller Create event; does not load the room or draw its map."""
        if self.created:
            return
        spawn = getattr(self.game, "instance_create", None)
        if not callable(spawn):
            raise NotImplementedError("RoomController requires game.instance_create")
        for point in self.readables:
            obj = spawn(point.x, point.y, "obj_readable_room1")
            obj.extflag = point.extflag
            obj.image_xscale = point.xscale
            obj.image_yscale = point.yscale
            self.spawned_readables.append(obj)
        if self.on_create is not None:
            self.on_create(self)
        self.created = True

    def request_interaction(self, extflag: str, times_talked: int = 0) -> bool:
        """Queue a named conversation, e.g. from obj_readable_room1's User 0."""
        if extflag not in self.handlers:
            return False
        if self.pending is not None or self.active_interaction is not None:
            return False
        self.pending = (extflag, times_talked)
        self._times_talked = times_talked
        self.npc_animate = False
        self.npc_animate_target = -4
        return True

    def show_convo(self, extflag: str, times_talked: int = 0) -> bool:
        """Compatibility entry point mirroring Torhouse's GML method name."""
        return self.request_interaction(extflag, times_talked)

    def _release(self) -> None:
        if self._owns_interact_lock:
            self._globals().interact = 0
            self._owns_interact_lock = False
        self.active_interaction = None
        self.con = -1

    def step(self) -> None:
        """Evaluate room story hooks, then start or finish an interaction."""
        if self.on_step is not None:
            self.on_step(self)
        if self.active_interaction is not None:
            if not self._dialogue_active():
                self._release()
            return
        if self.pending is None:
            return
        # Unlike raw GML 'con', do not steal another system's interaction lock.
        if self._dialogue_active() or self._globals().interact != 0:
            return
        extflag, count = self.pending
        self.pending = None
        self._globals().interact = 1
        self._owns_interact_lock = True
        self.active_interaction = extflag
        self.con = 100
        try:
            self.handlers[extflag](self, count)
        except Exception:
            self._release()
            raise

    def alarm_0(self) -> None:
        """Original Torhouse Alarm 0 only increments `con`."""
        self.con += 1

    def room_exit(self) -> None:
        """Release only the interaction lock owned by this controller.

        The room manager, not the controller, destroys room-local instances.
        """
        self.pending = None
        self._release()
        self.created = False
        self.spawned_readables.clear()


__all__ = ["ReadablePoint", "RoomController", "DialogueHandler", "CreateHook"]
