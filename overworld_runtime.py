"""Source-first GameMaker overworld-object adapter for the Tk Chapter 6 game.

This is the narrow bridge between the existing Tk/PIL game and recovered GML
objects.  Room *resources* remain in rooms.py; room-controller *instances* live
here. Nothing in this module replaces Player, AudioManager or DialogueWriter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from obj_interactable import Interactable
from obj_interactablesolid import InteractableSolid
from obj_mainchara_interactions import (
    decrement_interaction_buffer, mainchara_try_interact,
)
from obj_readable_room1 import ReadableRoom1
from obj_room_torhouse import TorhouseRoomController
from obj_solidblock import SolidBlock


@dataclass
class OverworldGlobals:
    """Subset of GameMaker's global state required by recovered objects."""

    chapter: int = 6
    plot: int = 0
    darkzone: int = 0
    facing: int = 0
    interact: int = 0
    msc: int = 0
    typer: int = 5
    fc: int = 0
    fe: int = 0
    msg: list[str] = field(default_factory=lambda: [""])
    flag: dict[int, int] = field(default_factory=dict)


def canonical_room_id(room_id: Any) -> str:
    """The source room controller is obj_room_torhouse; room ID may differ."""
    name = str(room_id)
    return "torhouse" if name in {"torhouse", "room_torhouse"} else name


@dataclass
class _DialoguerHandle:
    """Temporary instance handle for an obj_dialoguer backed by DialogueWriter."""
    game: Any
    x: float
    y: float

    @property
    def alive(self) -> bool:
        return bool(getattr(self.game.dialogue_writer, "active", False))


class OverworldRuntime:
    """Room lifecycle, object creation, collision lookup and Kris input bridge."""

    def __init__(self, game: Any) -> None:
        self.game = game
        self.room_id = ""
        self.controller: Any = None
        self.instances: list[Any] = []
        self.room_factories: dict[str, Callable[[Any], Any]] = {
            "torhouse": self._make_torhouse,
        }
        # Story text belongs to Chapter 6 content, not the room object.
        self.dialogue_handlers: dict[str, dict[str, Callable]] = {}
        self.room_coordinate_scale: float = 1.0

    def _make_torhouse(self, game: Any) -> TorhouseRoomController:
        return TorhouseRoomController(
            game,
            handlers=self.dialogue_handlers.get("torhouse", {}),
            dialogue_active=game.d_ex,
        )

    def register_room_controller(self, room_id: str, factory: Callable[[Any], Any]) -> None:
        self.room_factories[canonical_room_id(room_id)] = factory

    def register_room_handler(self, room_id: str, extflag: str, handler: Callable) -> None:
        room_id = canonical_room_id(room_id)
        self.dialogue_handlers.setdefault(room_id, {})[extflag] = handler
        if canonical_room_id(self.room_id) == room_id and self.controller is not None:
            self.controller.handlers[extflag] = handler

    def register_room_dialogue(
        self,
        room_id: str,
        extflag: str,
        messages: list[str] | tuple[str, ...] | str,
        *,
        options: dict | None = None,
    ) -> None:
        """Attach authored Chapter 6 dialogue to a room's named interaction."""
        pages = [messages] if isinstance(messages, str) else list(messages)
        def start(controller: Any, previous_reads: int) -> None:
            controller.game.start_dialogue(pages, options=options)
        self.register_room_handler(room_id, extflag, start)

    def leave_room(self) -> None:
        if self.controller is not None:
            self.controller.room_exit()
        for instance in list(self.instances):
            destroy = getattr(instance, "destroy", None)
            if callable(destroy):
                destroy()
            else:
                self.instance_destroy(instance)
        self.instances.clear()
        self.controller = None
        self.room_id = ""
        # Every new room starts without a stale room-owned interaction lock.
        self.game.global_state.interact = 0

    def enter_room(self, room_id: str, *, coordinate_scale: float = 1.0) -> None:
        self.leave_room()
        self.room_id = str(room_id)
        self.room_coordinate_scale = float(coordinate_scale)
        key = canonical_room_id(room_id)
        factory = self.room_factories.get(key)
        if factory is not None:
            self.controller = factory(self.game)
            self.controller.create()
            # Object positions are in source coordinates by default. Rooms
            # authored at other scales must declare their scale explicitly.
            if self.room_coordinate_scale != 1.0:
                for obj in self.instances:
                    obj.x *= self.room_coordinate_scale
                    obj.y *= self.room_coordinate_scale
                    obj.image_xscale *= self.room_coordinate_scale
                    obj.image_yscale *= self.room_coordinate_scale

    def instance_create(self, x: float, y: float, resource: Any) -> Any:
        if not isinstance(resource, str):
            resource = getattr(resource, "object_name", resource)
        if resource == "obj_readable_room1":
            obj = ReadableRoom1(
                self.game, x, y, room_id=self.room_id,
                room_controller=self.controller,
            )
        elif resource == "obj_interactable":
            obj = Interactable(self.game, x, y)
        elif resource == "obj_interactablesolid":
            obj = InteractableSolid(self.game, x, y)
        elif resource == "obj_solidblock":
            obj = SolidBlock(self.game, x, y)
        elif resource == "obj_dialoguer":
            # The recovered fallback uses a GameMaker dialoguer instance.
            # Bridge it to the existing Python dialogue writer, rather than
            # creating an empty UI window that never closes.
            messages = list(self.game.global_state.msg)
            messages = [message for message in messages if message]
            if messages:
                self.game.start_dialogue(messages)
            return _DialoguerHandle(self.game, x, y)
        else:
            raise NotImplementedError(
                f"Overworld instance factory has no port for {resource!r}"
            )
        self.instances.append(obj)
        return obj

    def instance_destroy(self, instance: Any) -> None:
        if instance in self.instances:
            self.instances.remove(instance)
        if hasattr(instance, "destroyed"):
            instance.destroyed = True

    def instance_exists(self, instance: Any) -> bool:
        if isinstance(instance, _DialoguerHandle):
            return instance.alive
        return instance in self.instances and not getattr(instance, "destroyed", False)

    def instances_of(self, resource: str) -> list[Any]:
        if resource == "obj_mainchara":
            player = getattr(self.game, "player", None)
            return [player] if player is not None else []
        return [obj for obj in self.instances if self._in_family(obj, resource)]

    @staticmethod
    def _in_family(instance: Any, resource: str) -> bool:
        if resource == "obj_interactable":
            return isinstance(instance, Interactable)
        if resource == "obj_interactablesolid":
            return isinstance(instance, InteractableSolid)
        if resource == "obj_solidblock":
            return isinstance(instance, SolidBlock)
        return getattr(instance, "object_name", "") == resource

    @staticmethod
    def object_bounds(obj: Any) -> tuple[float, float, float, float] | None:
        # A generic obj_interactable has no assigned sprite, so it needs an
        # explicitly supplied hitbox (width,height) from the room definition.
        sprite = getattr(obj, "sprite_metadata", None)
        if sprite is None:
            width = getattr(obj, "width", None)
            height = getattr(obj, "height", None)
            if width is None or height is None:
                return None
            origin_x = origin_y = 0
            left = top = 0
            right, bottom = width, height
        else:
            origin_x, origin_y = sprite.origin_x, sprite.origin_y
            left, top = sprite.bbox_left, sprite.bbox_top
            # GameMaker's bounding box right/bottom are inclusive.
            right, bottom = sprite.bbox_right + 1, sprite.bbox_bottom + 1
        sx = getattr(obj, "image_xscale", 1.0)
        sy = getattr(obj, "image_yscale", 1.0)
        x1, x2 = obj.x + (left - origin_x) * sx, obj.x + (right - origin_x) * sx
        y1, y2 = obj.y + (top - origin_y) * sy, obj.y + (bottom - origin_y) * sy
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    def collision_rectangle(
        self, x1: float, y1: float, x2: float, y2: float,
        resource: str, precise: bool = False, notme: bool = True,
    ) -> Any:
        # The GML passes reversed rectangle edges when facing left or up.
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        for obj in self.instances:
            if not self._in_family(obj, resource) or getattr(obj, "destroyed", False):
                continue
            bounds = self.object_bounds(obj)
            if bounds is None:
                continue
            a, b, c, d = bounds
            if right > a and left < c and bottom > b and top < d:
                return obj
        return -4

    def get_room_controller(self, name: str) -> Any:
        if canonical_room_id(name) == canonical_room_id(self.room_id):
            return self.controller
        return None

    def _sync_player(self) -> None:
        player = getattr(self.game, "player", None)
        if player is None:
            return
        anim = getattr(player, "animation", None)
        player.sprite_width = getattr(anim, "sprite_width", getattr(player, "sprite_width", 20))
        player.sprite_height = getattr(anim, "sprite_height", getattr(player, "sprite_height", 28))
        if not hasattr(player, "onebuffer"):
            player.onebuffer = 0
        if not hasattr(player, "interactedobject"):
            player.interactedobject = -4
        if not hasattr(player, "disable_interaction_checks"):
            player.disable_interaction_checks = False
        mapping = {"down": 0, "right": 1, "up": 2, "left": 3}
        self.game.global_state.facing = mapping.get(
            str(getattr(player, "facing", "down")).lower(),
            self.game.global_state.facing,
        )

    def try_interact(self) -> Any:
        self._sync_player()
        if self.controller is not None and (
            getattr(self.controller, "pending", None) is not None
            or getattr(self.controller, "active_interaction", None) is not None
        ):
            return None
        return mainchara_try_interact(
            self.game.player,
            state=self.game.global_state,
            confirm_pressed=True,
            collision_rectangle=self.collision_rectangle,
        )

    def step(self) -> None:
        self._sync_player()
        player = getattr(self.game, "player", None)
        # These counters advance on gameplay frames, not Tk key repeat events.
        if player is not None:
            decrement_interaction_buffer(player)
        if self.controller is not None:
            self.controller.step()
        for obj in list(self.instances):
            update = getattr(obj, "step", None)
            if callable(update):
                update()


__all__ = ["OverworldRuntime", "OverworldGlobals", "canonical_room_id"]
