"""Chapter 6 adaptation of GameMaker's obj_readable_room1.

Source: user-provided Create, Alarm 0, Step and Other 10 (User Event 0) GML.

Unlike the original monolithic User Event 0, room-specific chapter dialogue is
registered in a routing table or left with the room controller. This class keeps
the common interaction state machine and exact Torhouse delegation semantics.

This object inherits obj_interactable. The parent's User Event 0 only invokes
an optional on_interact callback; it does not detect interaction input.
Because this child overrides User Event 0 without event_inherited(), the
readable's own routing runs instead. The engine must still trigger event_user(0).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from obj_interactable import Interactable


@dataclass(frozen=True)
class ReadableSpriteMetadata:
    name: str = "spr_interactable"
    width: int = 20
    height: int = 20
    origin_x: int = 0
    origin_y: int = 0
    bbox_left: int = 0
    bbox_top: int = 0
    bbox_right: int = 19
    bbox_bottom: int = 19
    mask_type: str = "axis_aligned_rectangle"
    frames_per_game_frame: int = 1


SPR_INTERACTABLE = ReadableSpriteMetadata()


class ReadableRoutingTable:
    """Chapter-6-specific read action handlers, keyed by room and extflag.

    Handlers are invoked with (readable, prior_read_count). A handler should
    return True if it queues/starts a conversation, False otherwise. Routes
    can be exact or substring matches, matching GML's string_pos behavior.
    """
    def __init__(self) -> None:
        self._rules: list[tuple[str, str, bool, Callable[["ReadableRoom1", int], bool]]] = []

    def register(
        self,
        room_id: str,
        extflag: str,
        handler: Callable[["ReadableRoom1", int], bool],
        *,
        contains: bool = False,
    ) -> None:
        self._rules.append((room_id, extflag, contains, handler))

    def dispatch(self, obj: "ReadableRoom1") -> tuple[bool, bool]:
        for room_id, extflag, contains, callback in self._rules:
            if room_id not in (obj.room_id, "*"):
                continue
            if (extflag in str(obj.extflag)) if contains else (extflag == obj.extflag):
                return True, bool(callback(obj, obj.read))
        return False, False


class ReadableRoom1(Interactable):
    """One inspectable trigger placed in a room (NOT a room resource)."""

    object_name = "obj_readable_room1"
    parent_object = "obj_interactable"
    sprite_index_default = "spr_interactable"
    sprite_metadata = SPR_INTERACTABLE
    visible_default = False
    solid_default = False
    persistent_default = False
    uses_physics = False
    collision_shape = "circle"  # editor setting, Box2D physics is disabled

    def __init__(
        self,
        game: Any,
        x: float = 0,
        y: float = 0,
        *,
        image_xscale: float = 1.0,
        image_yscale: float = 1.0,
        room_id: str | None = None,
        extflag: str | int = 0,
        room_controller: Any = None,
        routing_table: ReadableRoutingTable | None = None,
        fallback_dialogue: Callable[["ReadableRoom1"], Any] | None = None,
        schedule_alarm: Callable[["ReadableRoom1", int, int], Any] | None = None,
        on_destroy: Callable[["ReadableRoom1"], Any] | None = None,
    ) -> None:
        super().__init__(game, x, y)
        self.room_id = room_id if room_id is not None else str(getattr(game, "room_id", ""))
        self.room_controller = room_controller
        self.routing_table = routing_table
        self.fallback_dialogue = fallback_dialogue
        self._schedule_alarm = schedule_alarm
        self._on_destroy = on_destroy
        self.image_xscale = image_xscale
        self.image_yscale = image_yscale
        self.destroyed = False
        self._pending_alarm_ticks: int | None = None
        self._owns_lock = False
        self._delegated_controller: Any = None
        self._delegated_accepted = False
        self.replacement = None
        self.create()
        self.extflag = extflag  # room controller assigns extflag *after* GameMaker Create

    def _global(self) -> Any:
        state = getattr(self.game, "global_state", None)
        if state is None:
            raise NotImplementedError("Requires game.global_state (global.interact, darkzone, chapter)")
        return state

    def _dialogue_active(self) -> bool:
        fn = getattr(self.game, "d_ex", None)
        if not callable(fn):
            raise NotImplementedError("Supply game.d_ex() for checking active dialogue")
        return bool(fn())

    def create(self) -> None:
        """GML Create: initializes state; replaces a School Door trigger in Ch2+."""
        self.myinteract = 0
        self.image_speed = 0
        self.read = 0
        self.tempvar = 0
        self.extflag = 0
        self.mydialoguer = -1
        self.skip = 0
        self.selfdestruct = False
        g = self._global()
        if (
            int(getattr(g, "chapter", 6)) >= 2
            and self.room_id == "room_schooldoor"
            and 270 <= self.x <= 470
        ):
            spawn = getattr(self.game, "instance_create", None)
            if not callable(spawn):
                raise NotImplementedError("School Door conversion requires game.instance_create")
            dwt = spawn(self.x, self.y, "obj_dw_transition_interactable")
            dwt.image_xscale = self.image_xscale
            dwt.image_yscale = self.image_yscale
            self.replacement = dwt
            self.destroy()

    def destroy(self) -> None:
        if self.destroyed:
            return
        self.destroyed = True
        if self._owns_lock:
            self._global().interact = 0
            self._owns_lock = False
        if self._on_destroy is not None:
            self._on_destroy(self)
        else:
            destroy = getattr(self.game, "instance_destroy", None)
            if callable(destroy):
                destroy(self)

    def alarm_0(self) -> None:
        """GML Alarm[0]: destroy this instance."""
        self.destroy()

    def _queue_alarm_0(self, frames: int) -> None:
        if self._schedule_alarm is not None:
            self._schedule_alarm(self, 0, frames)
        else:
            # Engine-independent test fallback. Real engine should use alarm slots.
            self._pending_alarm_ticks = frames

    def _release_own_lock(self) -> None:
        # Never release a lock subsequently owned by a room controller.
        if self._owns_lock:
            self._global().interact = 0
            self._owns_lock = False

    def _resolve_room_controller(self) -> Any:
        if self.room_controller is not None:
            return self.room_controller
        getter = getattr(self.game, "get_room_controller", None)
        if callable(getter):
            return getter("room_torhouse")
        return None

    def _dispatch_torhouse(self) -> bool:
        """Returns True iff the GML would set skip=1 for this extflag."""
        flag = str(self.extflag)
        if "torhouse_" in flag:
            ctrl = self._resolve_room_controller()
            if ctrl is not None:
                result = ctrl.show_convo(flag, self.read)
                self._delegated_accepted = result is not False
                if self._delegated_accepted:
                    self._delegated_controller = ctrl
            return True
        # The Chapter-5 LW02 branch was a distinct cutscene controller.
        # Preserve the skip behavior; allow an explicitly installed Chapter-6
        # replacement route, but NEVER invoke the Chapter-5 cutscene by default.
        if "tortoast_" in flag:
            if self.routing_table is not None:
                matched, accepted = self.routing_table.dispatch(self)
                if matched:
                    self._delegated_accepted = accepted
            return True
        return False

    def event_user(self, number: int) -> bool:
        if number != 0:
            raise NotImplementedError(f"Only User Event 0 is provided (got {number})")
        return self.user_event_0()

    def user_event_0(self) -> bool:
        """GML Other 10, with Chapter-5-specific dialogue extracted.

        Returns whether a room-specific route accepted the interaction.
        Even an unhandled event increments `read`, matching GML.
        """
        if self.destroyed or self.myinteract == 3:
            return False
        g = self._global()
        self.myinteract = 3
        g.msc = 0
        g.typer = 6 if getattr(g, "darkzone", 0) == 1 else 5
        g.fe = 0
        g.fc = 0
        g.interact = 1
        self._owns_lock = True
        self.skip = 0
        self._delegated_controller = None
        self._delegated_accepted = False
        # Darkcontroller's charcon=0 is a GameMaker-side auxiliary effect.
        reset = getattr(self.game, "reset_darkcontroller_charcon", None)
        if callable(reset):
            reset()

        routed = False
        accepted = False
        if self.room_id in ("room_torhouse", "torhouse"):
            routed = self._dispatch_torhouse()
            accepted = self._delegated_accepted
        if not routed and self.routing_table is not None:
            routed, accepted = self.routing_table.dispatch(self)
            if routed:
                self._delegated_accepted = accepted
        self.read += 1
        if routed:
            self.skip = 1
            self._release_own_lock()
            self.skip = 0
            return accepted

        if self.fallback_dialogue is not None:
            # Direct dialogue is used only when Chapter 6 supplies it.
            self.mydialoguer = self.fallback_dialogue(self)
            return True

        # We don't fabricate the original GML placeholder or Chapter-5 prose.
        self.myinteract = 0
        self._release_own_lock()
        return False

    def step(self) -> None:
        if self.destroyed:
            return
        if self._pending_alarm_ticks is not None:
            self._pending_alarm_ticks -= 1
            if self._pending_alarm_ticks <= 0:
                self._pending_alarm_ticks = None
                self.alarm_0()
                return
        if self.myinteract != 3:
            return
        # The queued dialogue may not open until the room controller's Step.
        # Don't clear the readable state while its controller is pending.
        ctrl = self._delegated_controller
        if ctrl is not None and getattr(ctrl, "pending", None) is not None:
            return
        if self._dialogue_active():
            return
        self._release_own_lock()
        self.myinteract = 0
        mainchara = getattr(self.game, "mainchara", None)
        if mainchara is not None:
            mainchara.onebuffer = 3
        if self.selfdestruct:
            self._queue_alarm_0(2)
        self._delegated_controller = None
        self._delegated_accepted = False


obj_readable_room1 = ReadableRoom1

__all__ = ["ReadableRoom1", "ReadableRoutingTable", "SPR_INTERACTABLE", "obj_readable_room1"]
