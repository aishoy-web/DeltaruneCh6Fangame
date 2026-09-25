"""Room, exit, interactable, trigger, and collision-world definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from collision import (
    DEFAULT_SOLID_CATEGORIES,
    Collider,
    CollisionWorld,
    Rect,
    coerce_collider,
)
from dialogue import Dialogue, DialogueScript


@dataclass
class Exit:
    x: int
    y: int
    width: int
    height: int
    destination: str
    spawn_x: int
    spawn_y: int
    facing_direction: str | None = None
    # transition: str
    # sound: str
    # required_flag: str


@dataclass
class Interactable:
    x: int
    y: int
    width: int
    height: int
    action: str
    data: object | None = None
    facing: str | None = None


@dataclass
class DialogueTrigger:
    id: str
    x: int
    y: int
    width: int
    height: int
    dialogue: DialogueScript | list[Dialogue]
    flag: str | None = None
    once: bool = True


@dataclass(init=False)
class Room:
    name: str
    background: str
    music: str | None
    dialogue: DialogueScript | list[Dialogue]
    collisions: list[Collider]
    dynamic_colliders: list[Collider]
    exits: list[Exit]
    interactable_objects: list[Interactable]
    npcs: list[Any]
    triggers: list[DialogueTrigger]
    items: list[Any]
    collision_world: CollisionWorld = field(init=False, repr=False)

    def __init__(
        self,
        name: str,
        background: str,
        collisions: Iterable[Any] | None,
        music: str | None = None,
        dialogue: Iterable[Dialogue] | DialogueScript | None = None,
        exits: Iterable[Exit] | None = None,
        interactable_objects: Iterable[Interactable] | None = None,
        npcs: Iterable[Any] | None = None,
        triggers: Iterable[DialogueTrigger] | None = None,
        items: Iterable[Any] | None = None,
        dynamic_colliders: Iterable[Any] | None = None,
    ) -> None:
        self.name = name
        self.background = background
        self.music = music
        self.dialogue = (
            dialogue
            if isinstance(dialogue, DialogueScript)
            else list(dialogue or [])
        )
        self.exits = list(exits or [])
        self.interactable_objects = list(interactable_objects or [])
        self.npcs = list(npcs or [])
        self.triggers = list(triggers or [])
        self.items = list(items or [])

        # Accept old (x, y, width, height) tuples while standardizing all room
        # geometry on Collider objects for the runtime.
        self.collisions = [coerce_collider(value) for value in (collisions or [])]
        self.dynamic_colliders = [
            coerce_collider(value) for value in (dynamic_colliders or [])
        ]
        self.collision_world = CollisionWorld(
            self.collisions,
            self.dynamic_colliders,
        )

        # Keep these as the exact lists owned by CollisionWorld so additions or
        # removals remain visible through both APIs.
        self.collisions = self.collision_world.colliders
        self.dynamic_colliders = self.collision_world.dynamic_colliders

    def place_meeting(
        self,
        hitbox: Rect | object,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        *,
        categories: Iterable[str] | None = DEFAULT_SOLID_CATEGORIES,
    ) -> bool:
        """Python equivalent of ``place_meeting(..., obj_solidblock)``."""

        return self.collision_world.place_meeting(
            hitbox,
            offset_x,
            offset_y,
            categories=categories,
        )

    def collisions_in_rect(
        self,
        rect: Rect | object,
        *,
        categories: Iterable[str] | None = None,
        blocking_only: bool = False,
    ) -> list[Collider]:
        return self.collision_world.collisions_in_rect(
            rect,
            categories=categories,
            blocking_only=blocking_only,
        )

    def add_collider(self, collider: Any, *, dynamic: bool = False) -> Collider:
        return self.collision_world.add(collider, dynamic=dynamic)

    def remove_collider(self, collider: Collider) -> None:
        self.collision_world.remove(collider)
