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
    # music=bedroom.music,
    interactable_objects = [Interactable(
        x=80,
        y=36,
        width=48,
        height=28,
        action="dialogue",
        data="obj_kris_bedroom_bed_0",),],
    dialogue=[Dialogue(voice=None,text_id="obj_kris_bedroom_bed_0",choices=None,scene_id=None,sound_effect=None)],
    exits=[Exit(x=290,
                y=110,
                width=20,
                height=20,
                destination="myroom",
                spawn_x=150,
                spawn_y=165),
                ])

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
    music="You Can Always Come Home.mp3",
    dialogue=[Dialogue(voice=None,text_id="obj_hallway_toriel_door_0",choices=None,scene_id=None,sound_effect=None)],
    exits=[Exit(x=145,
                y=220,
                width=40,
                height=20,
                destination="myhallway",
                spawn_x=285,
                spawn_y=95)])
livingroom = Room(name="torhouse", background= "bg_torhouse_bg",
                  collisions=[
                      (0,0,0,0), #bottom wall
                      ])

ROOMS = {"myroom": bedroom, # Keep this room dictionary at the end of rooms.py so other files can reference it.
         "myhallway": hallway,
         "torhouse_bg": livingroom,}