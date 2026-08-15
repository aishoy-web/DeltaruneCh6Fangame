#Different from room.py, this file stores the details of what rooms are used in the game.
#It imports the Room class from room.py and creates instances of it for each room in the game. 
#It also establishes the exits for each room, allowing the player to move between them.
from dataclasses import dataclass
from room import Room, Exit, Interactable, DialogueTrigger
from dialogue import Dialogue
from pathlib import Path
BASE_DIR = Path(__file__).parent
'''
    Each room has a background image, collision boxes for the walls and objects, interactable objects, and exits to other rooms. 
    Each room also has dialogue that can be triggered by interacting with multiple objects in the room.
    
    information about the background image:
        -The background image must be a PNG file in the room_backgrounds folder. 
        -at minimum it should be 320 x 240.
    
    information about the collisions:
        -The collisions are defined as a list of tuples, where each tuple represents a rectangular area that the player cannot walk through.
        -the tuples are defined as (x1, y1, x2, y2), where (x1, y1) is the top left corner of the rectangle, 
            and (x2, y2) is the bottom right corner of the rectangle.
    
    information about the music data:
        -The music data is a string that represents the filename of the music file to be played in the room.
        -it must be in the mus folder.
    
    information about the interactable objects:
        -The interactable objects are defined as a list of Interactable instances.
        -Each Interactable instance has an x, y, width, height, action, and data attribute.
        -The x and y attributes represent the position of the object.
        -The width and height attributes represent the size of the object. (which should ideally end where the collision box does)
        -The action attribute represents the action to be taken when the object is interacted with. (Dialogue, Scene, Noise, etc.)
        -The data attribute represents the data associated with the object.

    information about the dialogue:
        -The dialogue is defined as a list of Dialogue instances. Each one should be associated with an instance of an Interactable object, 
            and the text_id should match the data attribute of that Interactable object.
        -Each dialogue has a "voice" of a character who is present in speaking, (TODO) though in the future this should be modified
            to a list of characters who are present in the scene, and the voice should be associated with a character in that list,
            or it should be modified to be handled by a different system so that multiple voices can speak.
        -The text_id attribute represents the text to be displayed when the dialogue is triggered.
        -TODO: prolly in the future it should have a faceplate attribute, but not immediate for rn.
    
    information about the exits:
        -The exits are defined as a list of Exit instances.
        -Each Exit instance has an x, y, width, height, destination, spawn_x, spawn_y, and facing_direction attribute.
        -The x and y attributes represent the position of the exit.
        -The width and height attributes represent the size of the exit.
        -The destination attribute represents the name of the room that the exit leads to.
        -The spawn_x and spawn_y attributes represent the position of the player when they enter the new room.
        -The facing_direction attribute represents the direction the player will be facing when they enter the new room.
        
    see this bedroom below for reference.
        
'''

bedroom = Room(
    name="myroom",
    background="Dreemurr_residence_location_Kris's_room_night.png",
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
    interactable_objects = [
            #your bed
            Interactable(
            x=240,
            y=108,
            width=48,
            height=28,
            action="dialogue",
            data="obj_kris_bedroom_bed_0",),
                  
            # asriels bed              
            Interactable(
            x=80,
            y=36,
            width=48,
            height=28,
            action="dialogue",
            data="obj_kris_bedroom_asriel_bed_0",),],
    dialogue=[
        Dialogue(
            voice=None,
            text_id="obj_kris_bedroom_bed_0",
            choices=None,
            scene_id=None,
            sound_effect=None),
        
        Dialogue(
            voice=None,
            text_id="obj_kris_bedroom_asriel_bed_0",
            choices=None,
            scene_id=None,
            sound_effect=None)],
    exits=[Exit(x=145,
                y=220,
                width=40,
                height=20,
                destination="myhallway",
                spawn_x=290,
                spawn_y=105,
                facing_direction="down")])

hallway = Room(
    name="myhallway",
    background="bg_myhallway_night.png",
    collisions = [(58,100,419,128), # top left wall, done (x1,y1,x2,y2),
                  (50,100,58,167), # left wall, done
                  (458,100,478,128), # top right wall, done
                  (478,128,500,167), # right wall, done
                  (58,167,478,180), #bottom wall
                  ],
    music="mus_birdnoise.ogg",
    interactable_objects = None,
    dialogue=[Dialogue(voice=None,text_id="obj_hallway_toriel_door_0",choices=None,scene_id=None,sound_effect=None)],
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

livingroom = Room(
    name="torhouse",
    background="bg_torhouse_bg_night.png",
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
    interactable_objects = None,
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