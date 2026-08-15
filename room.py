#The purpose of this file is to establish room, exit, and interactable logic.
from dataclasses import dataclass, field
from dialogue import Dialogue
@dataclass
class Exit:
    x: int
    y: int
    width: int
    height: int
    destination: str
    spawn_x: int
    spawn_y: int
    facing_direction: str = None
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
    dialogue: list
    flag: str | None = None
    once: bool = True
@dataclass
class Room:
    name: str
    background: str
    music: str
    dialogue: list
    collisions: list
    exits: list[Exit]
    triggers: list[DialogueTrigger] = field(default_factory=list)
    def __init__(
        self,
        name,
        background,
        collisions,
        music=None,
        dialogue=None,
        exits=None,
        interactable_objects = None,
        npcs=None,
        triggers=None,
        items=None,):
        self.name = name
        self.background = background
        self.collisions = collisions
        self.music = music
        self.dialogue = dialogue if dialogue else []
        self.exits = exits if exits else []
        self.interactable_objects = (interactable_objects if interactable_objects else [])
        self.npcs = npcs if npcs else []
        self.triggers = triggers if triggers else []
        self.items = items if items else []