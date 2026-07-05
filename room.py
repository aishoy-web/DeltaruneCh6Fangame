from dataclasses import dataclass,field
from dialogue import Dialogue
@dataclass
class Room:
    name:str
    background:str
    music:str|None = None
    dialogue:list = field(default_factory=list)
    exits:dict = field(default_factory=dict)

bedroom = Room(name="Bedroom",background="bedroom.png",music="You Can Always Come Home.mp3",dialogue=[Dialogue(voice=None,text="*Test. Insert very long text.",choices=None,scene_id=None,sound_effect=None)])
hallway = Room(name="Hallway",background="hallway.png",exits={"leftup": "bedroom","rightup": "kitchen"})

bedroom.exits["down"] = hallway
hallway.exits["up"] = bedroom