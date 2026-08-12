#Different from room.py, this file stores the details of what rooms are used in the game.
#It imports the Room class from room.py and creates instances of it for each room in the game. 
#It also establishes the exits for each room, allowing the player to move between them.
from room import Room, Exit, Interactable
from dialogue import Dialogue
from pathlib import Path
BASE_DIR = Path(__file__).parent
hallway = Room(
    name="myhallway",
    background="bg_myhallway.png",
    collisions = [(58,100,419,128), # top left wall, done (x1,y1,x2,y2),
                  (50,100,58,167), # left wall, done
                  (458,100,478,128), # top right wall, done
                  (478,128,500,167), # right wall, done
                  (58,167,478,180), #bottom wall
                  ],
    music="mus_birdnoise.ogg",
    interactable_objects = [Interactable(
        x=80,
        y=36,
        width=48,
        height=28,
        action="dialogue",
        data="obj_kris_bedroom_bed_0",),],
    dialogue=[Dialogue(voice=None,text_id="obj_kris_bedroom_bed_0",choices=None,scene_id=None,sound_effect=None)],
    exits=[
        Exit(
            x=290,
            y=110,
            width=20,
            height=20,
            destination="myroom",
            spawn_x=155,
            spawn_y=165,
            facing_direction="up"
        ),
        Exit(
            x=420,
            y=100,
            width=40,
            height=20,
            destination="torhouse",
            spawn_x=145,
            spawn_y=80,
            facing_direction="down",
        ),
    ],
)

bedroom = Room(
    name="myroom",
    background="Dreemurr_residence_location_Kris's_room.png",
    collisions = [
        (0, 0, 320, 100),      # top wall, done
        (0, 0, 40, 250),      # left wall, done
        (280, 0, 320, 250),   # right wall, done
        (185, 200, 320, 240),   # bottom right wall, done
        (0, 200, 145, 240),  # bottom left wall, done

        # bed_kris, done
        (232.5, 100, 280, 157.5),

        # bed_asriel
        (40,100,90,157.5),

        # dresser_kris
        (190, 100, 232.5, 117.5),

        # dresser_asriel
        (90,100,135,117.5)
          ],
    music="mus_birdnoise.ogg",
    dialogue=[Dialogue(voice=None,text_id="obj_hallway_toriel_door_0",choices=None,scene_id=None,sound_effect=None)],
    exits=[Exit(x=145,
                y=220,
                width=40,
                height=20,
                destination="myhallway",
                spawn_x=290,
                spawn_y=105,
                facing_direction="down")])
livingroom = Room(
    name="torhouse",
    background="bg_torhouse_bg.png",
    collisions=[
        (70, 200, 650, 240), # Bottom wall
        (173,40,210,161), # Fridge wall
        (230,100,345,141), # Kitchen wall
        (115,40,140,161), # Top left wall
        (345,100,420,166), # Phone wall
        (475,130,520,157.5), # TV stand
        (430,120,580,140) # Top backup wall, hopefully the player never touches this
    ],
    music = None,
    interactable_objects= None,
    dialogue= None,
    exits=[Exit(x=145,
                y=70,
                width=40,
                height=20,
                destination="myhallway",
                spawn_x=430,
                spawn_y=100,
                facing_direction="down")]

)

ROOMS = {"myroom": bedroom, # Keep this room dictionary at the end of rooms.py so other files can reference it.
         "myhallway": hallway,
         "torhouse": livingroom,}