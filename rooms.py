from room import Room
from dialogue import Dialogue
bedroom = Room(name="Kris_Bedroom",background="Dreemurr_residence_location_Kris's_room.png",music="You Can Always Come Home.mp3",dialogue=[Dialogue(voice=None,text="*Test. Insert very long text.",choices=None,scene_id=None,sound_effect=None)])

hallway = Room(
    name="Hallway",
    background="hallway.png")

bedroom.exits["down"] = hallway
hallway.exits["up"] = bedroom