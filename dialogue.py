from dataclasses import dataclass
@dataclass
class Dialogue:
    voice:object
    text_id:str
    choices:list|None = None
    scene_id:str|None = None
    sound_effect:object|None = None
