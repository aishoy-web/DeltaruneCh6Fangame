"""Data port of gml_GlobalScript_scr_encountersetup (Chapter 5 snapshot).

All source coordinates are in GameMaker's 640x480 logical coordinate system.
The Chapter 6 Tkinter game renders at 320x240, so battle rendering halves these
coordinates. Resource IDs are retained as names until corresponding Python
battle enemy classes/sprites are implemented.

Do not renumber these IDs for Chapter 6: new encounters can be registered with
register_encounter() without changing the original data.
"""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
import random

from battle import EnemySpawn


@dataclass(frozen=True, slots=True)
class EnemyDefinition:
    object_name: str
    monster_type: int
    x: float
    y: float


@dataclass(slots=True)
class EncounterLayout:
    number: int
    enemy_definitions: list[EnemyDefinition]
    enemy_slots: list[EnemySpawn | None]
    hero_positions: list[tuple[float, float]]
    battle_message: str
    camera_origin: tuple[float, float] = (0, 0)
    resource_names: list[str | None] = field(default_factory=list)


# Every case only stores overrides to the common defaults. A missing case is
# handled using the GML switch default, not silently treated as an empty fight.
# Entries: encounter_id: (active enemies [(object, type, x, y)], hero overrides, text)
# Hero overrides are keyed by (slot, axis); an omitted text uses '* It is known.'
SOURCE_ENCOUNTERS = {
    0: ([('obj_baseenemy', 1, 500, 40)], {}, None),
    1: ([('obj_baseenemy', 1, 480, 110), ('obj_baseenemy', 1, 500, 200)], {}, '* Test enemies showed up.'),
    2: ([('obj_lancerboss', 2, 540, 200)], {}, None),
    3: ([('obj_dummyenemy', 3, 500, 160)], {}, None),
    4: ([('obj_diamondenemy', 5, 480, 140)], {}, '* Rudinn drew near!'),
    5: ([('obj_diamondenemy', 5, 480, 110), ('obj_diamondenemy', 5, 500, 200)], {}, '* A necklace of Rudinns blocks your path.'),
    6: ([('obj_diamondenemy', 5, 480, 110), ('obj_heartenemy', 6, 500, 200)], {}, '* Rudinn and Hathy blocked the way!'),
    7: ([('obj_smallcheckers_enemy', 9, 440, 150)], {}, "* C. Round attacked violently!&* (You recall Ralsei's advice to include Susie in an ACT.)"),
    8: ([('obj_clubsenemy', 16, 400, 120)], {}, '* Clover grew close!'),
    9: ([('obj_heartenemy', 6, 480, 20), ('obj_heartenemy', 6, 500, 120), ('obj_heartenemy', 6, 460, 220)], {}, '* Three Hathys blocked the way!'),
    12: ([('obj_checkers_enemy', 10, 480, 120)], {}, '* Here it comes!'),
    13: ([('obj_ponman_enemy', 11, 480, 110), ('obj_ponman_enemy', 11, 500, 200)], {}, '* Ponman drew near!'),
    14: ([('obj_ponman_enemy', 11, 480, 20), ('obj_ponman_enemy', 11, 500, 120), ('obj_ponman_enemy', 11, 460, 220)], {}, '* Ponman drew near!'),
    15: ([('obj_clubsenemy', 7, 400, 30), ('obj_heartenemy', 6, 420, 200)], {}, '* Clover and Hathy grew close!'),
    16: ([('obj_rabbick_enemy', 13, 480, 140)], {}, '* Rabbick slithered in the way!'),
    17: ([('obj_rabbick_enemy', 13, 480, 60), ('obj_rabbick_enemy', 13, 460, 180)], {}, '* Rabbicks slithered in the way!'),
    18: ([('obj_bloxer_enemy', 14, 480, 140)], {}, '* Bloxer assembled!'),
    19: ([('obj_bloxer_enemy', 14, 480, 60), ('obj_bloxer_enemy', 14, 460, 180)], {}, '* Bloxers assembled!'),
    20: ([('obj_lancerboss2', 12, 480, 160)], {(0, 'x'): 120}, '* Lancer blocked the way!'),
    21: ([('obj_jigsawryenemy', 15, 480, 140)], {}, '* Jigsawry drew near!'),
    22: ([('obj_jigsawryenemy', 15, 480, 20), ('obj_jigsawryenemy', 15, 500, 120), ('obj_jigsawryenemy', 15, 460, 220)], {}, '* A board of Jigsawrys blocked the way!'),
    23: ([('obj_jigsawryenemy', 15, 480, 20), ('obj_diamondenemy', 5, 500, 120), ('obj_heartenemy', 6, 460, 220)], {}, '* Smorgasboard.'),
    24: ([('obj_rabbick_enemy', 13, 480, 60), ('obj_diamondenemy', 5, 460, 180)], {}, '* Rabbick slithered in the way!'),
    25: ([('obj_joker', 20, 500, 160)], {(0, 'x'): 80, (0, 'y'): 100, (1, 'x'): 90, (1, 'y'): 150, (2, 'x'): 100, (2, 'y'): 210}, '* LET THE GAMES BEGIN!'),
    27: ([('obj_checkers_enemy', 21, 480, 120)], {(0, 'y'): 65}, '* Here it comes^1. Again.'),
    28: ([('obj_rudinnranger', 22, 480, 110), ('obj_rudinnranger', 22, 500, 200)], {}, '* Rudinn Rangers came sparkling into view!'),
    29: ([('obj_headhathy', 23, 480, 110), ('obj_headhathy', 23, 500, 200)], {}, '* Head Hathy blocked the way quietly!'),
    30: ([('obj_headhathy', 23, 480, 20), ('obj_headhathy', 23, 500, 120), ('obj_headhathy', 23, 460, 220)], {}, '* Head Hathy blocked the way quietly! (x3)'),
    31: ([('obj_susieenemy', 19, 520, 80), ('obj_lancerboss3', 18, 540, 240)], {}, '* Two bad guys blocked the way!'),
    32: ([('obj_rabbick_enemy', 13, 480, 20), ('obj_rabbick_enemy', 13, 500, 120), ('obj_rabbick_enemy', 13, 460, 220)], {}, '* Rabbicks slithered in the way!'),
    33: ([('obj_diamondenemy', 5, 480, 20), ('obj_heartenemy', 6, 500, 120), ('obj_diamondenemy', 5, 460, 220)], {}, '* Various guys appeared!'),
    40: ([('obj_king_boss', 25, 460, 70)], {}, '* King blocked the way!'),
    71: ([('obj_clubsenemy', 47, 400, 80)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Clover joins the stage!'),
    72: ([('obj_dojograzeenemy', 42, 440, 100)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, "* It's a grazing adventure."),
    89: ([('obj_tasque_manager_enemy', 42, 487, 94)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Graze!'),
    90: ([('obj_werewire_enemy', 33, 476, 70), ('obj_werewire_enemy', 33, 454, 168)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Round One!'),
    91: ([('obj_poppup_enemy', 31, 412, 40), ('obj_omawaroid_enemy', 30, 466, 106), ('obj_virovirokun_enemy', 35, 412, 184)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Round Two!'),
    92: ([('obj_tasque_enemy', 32, 432, 52), ('obj_tasque_enemy', 32, 476, 140), ('obj_maus_enemy', 34, 512, 236)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Round Three!'),
    93: ([('obj_swatchling_enemy', 36, 394, 8), ('obj_swatchling_enemy', 36, 490, 74), ('obj_swatchling_enemy', 36, 394, 160)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Round Four!'),
    94: ([('obj_werewerewire_enemy', 40, 464, 68), ('obj_werewerewire_enemy', 40, 494, 184)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Final Round!'),
    100: ([('obj_dojo_spareenemy', 52, 440, 100)], {(0, 'x'): 94, (0, 'y'): 50, (1, 'x'): 80, (1, 'y'): 122, (2, 'x'): 72, (2, 'y'): 200}, '* Jigsaw Joe jigs in!'),
    200: ([('obj_floradinn_enemy', 70, 480, 110), ('obj_floradinn_enemy', 70, 500, 200)], {}, '* Floradinn florads in!'),
    201: ([('obj_leafling_enemy', 71, 510, 80), ('obj_leafling_enemy', 71, 540, 200)], {}, '* Leafling floats by carefree.'),
    202: ([('obj_scarecrow_enemy', 72, 450, 50), ('obj_kawkaw_enemy', 74, 487, 208)], {}, '* Shi blocks the way! (... sort of.)&* Kawkaw wants to play!'),
    203: ([('obj_shinobeetle_enemy', 73, 473, 50), ('obj_shinobeetle_enemy', 73, 520, 160)], {}, '* Shinobeetle sneaks in!'),
    204: ([('obj_kawkaw_enemy', 74, 480, 110), ('obj_kawkaw_enemy', 74, 500, 200)], {}, '* Kawkaw wants to play!'),
    205: ([('obj_sheary_enemy', 75, 461, 60), ('obj_sheary_enemy', 75, 503, 183)], {}, '* Sheary cuts in!'),
    206: ([('obj_netskie_enemy', 76, 473, 130)], {}, '* Netskie unwraps itself from its big fluffy tail!'),
    207: ([('obj_terracota_enemy', 77, 446, 76)], {}, '* Terakota stomps towards you!'),
    208: ([('obj_floradinn_enemy', 70, 458, 60), ('obj_leafling_enemy', 71, 500, 180)], {}, '* Floradinn florads in!&* Leafling floats by carefree.'),
    209: ([('obj_shinobeetle_enemy', 73, 473, 50), ('obj_leafling_enemy', 71, 540, 200)], {}, '* Shinobeetle sneaks in!&* Floradinn florads in!'),
    210: ([('obj_scarecrow_enemy', 72, 473, 24), ('obj_kawkaw_enemy', 74, 446, 153), ('obj_kawkaw_enemy', 74, 483, 240)], {}, '* Shi blocks the way! (... sort of.)&* Kawkaw wants to play!'),
    211: ([('obj_scarecrow_enemy', 72, 473, 32), ('obj_scarecrow_enemy', 72, 473, 162)], {}, '* Shi blocks the way! (... sort of.)'),
    212: ([('obj_scarecrow_enemy', 72, 473, 76)], {}, '* Shi blocks the way! (... sort of.)'),
    213: ([('obj_shinobeetle_enemy', 73, 474, 24)], {}, 'SETH AND 1 SHINOBEETLE'),
    214: ([('obj_floradinn_enemy', 70, 473, 64), ('obj_floradinn_enemy', 70, 446, 152), ('obj_floradinn_enemy', 70, 483, 240)], {}, "* It's a din of Floradinns!"),
    215: ([('obj_leafling_enemy', 71, 470, 80), ('obj_sheary_enemy', 75, 490, 180)], {}, '* A leaf and its cutter appeared!'),
    220: ([('obj_aqua_enemy', 112, 480, 130)], {}, '* A mysterious festival begins.'),
    221: ([('obj_orange_enemy', 113, 500, 103), ('obj_green_enemy', 114, 493, 180)], {}, '* Green brings the food!&* Orange brings the fight!'),
    222: ([('obj_blue_enemy', 115, 466, 40), ('obj_yellow_enemy', 116, 500, 160)], {}, "* Yellow brings the gun's!&* Blue brings the elegance!"),
    223: ([('obj_purple_enemy', 117, 480, 110), ('obj_aqua_enemy', 112, 500, 200)], {}, '* Aqua brings the sword!&* Seth brings the pen!'),
    224: ([('obj_pink_enemy', 118, 470, 131)], {}, '* TP MAX reduced by TEA!&Gather HEARTS to recover MAX TP!'),
    225: ([('obj_flowery_enemy', 119, 500, 114)], {}, '* Flowery faces you!'),
    226: ([('obj_floradinn_enemy', 70, 298, 158), ('obj_floradinn_enemy', 70, 420, 194)], {(0, 'x'): 90, (0, 'y'): 32, (1, 'x'): 80, (1, 'y'): 104}, ''),
    227: ([('obj_floradinn_enemy', 70, 480, 110)], {}, '* Floradinn florads in!'),
    228: ([('obj_floradinn_enemy', 70, 514, 38), ('obj_sheary_enemy', 75, 534, 130), ('obj_netskie_enemy', 76, 528, 222)], {}, '* Floradinn florads in!&* Sheary cuts in!&* Netskie unwraps itself from its big fluffy tail!'),
    229: ([('obj_netskie_enemy', 76, 473, 130)], {}, '* Netskie tricked you!'),
    230: ([('obj_floradinn_enemy', 70, 360, 158)], {(0, 'x'): 90, (0, 'y'): 32, (1, 'x'): 90, (1, 'y'): 104}, ''),
    231: ([('obj_scarecrow_enemy', 72, 462, 110)], {}, '* Shi blocks the way! (... sort of.)'),
    232: ([('obj_shinobeetle_enemy', 73, 437, 112)], {}, '* Shinobeetle is no longer alone!'),
    233: ([('obj_scarecrow_enemy', 72, 495, 75), ('obj_scarecrow_enemy', 72, 495, 130), ('obj_scarecrow_enemy', 72, 495, 185)], {}, '* Shi blocks the way for real!'),
    234: ([('obj_trashy_trio', 121, 456, 182)], {}, "* The world's most popular trio!"),
    235: ([('obj_enemy_example', 123, 456, 102)], {}, '...'),
    500: ([('obj_multiboss_enemy1', 500, 480, 80), ('obj_multiboss_enemy2', 500, 500, 160), ('obj_multiboss_enemy3', 500, 520, 240)], {}, '* A multiboss example showed up.'),
    501: ([('obj_multiboss_controller_enemy1', 501, 480, 80), ('obj_multiboss_controller_enemy2', 501, 500, 160), ('obj_multiboss_controller_enemy3', 501, 520, 240)], {}, '* A multiboss example with controller showed up.'),
    777: ([('obj_bullettester_enemy', 1, 500, 40), ('obj_bullettester_enemy', 1, 520, 130), ('obj_bullettester_enemy', 1, 540, 220)], {}, ' '),
}

# Three slots are always initialized before the switch statement.
DEFAULT_SLOTS = [
    ("obj_baseenemy", 1, 500, 40),
    ("obj_baseenemy", 0, 520, 130),
    ("obj_baseenemy", 0, 540, 220),
]
FALLBACK_ENEMIES = [
    ("obj_baseenemy", 1, 480, 110),
    ("obj_baseenemy", 1, 500, 200),
]

# Chapter 6 can register new definitions without modifying the ported table.
CUSTOM_ENCOUNTERS: dict[int, tuple[list[tuple[str, int, float, float]], str]] = {}


def register_encounter(number: int, enemies: Sequence[tuple[str, int, float, float]],
                       message: str) -> None:
    """Register a Chapter 6 encounter. Coordinates use 640x480 battle units."""
    number = int(number)
    if number in SOURCE_ENCOUNTERS:
        raise ValueError(f"Encounter ID {number} already exists in the Chapter 5 roster")
    if len(enemies) > 3:
        raise ValueError("Up to three enemy slots are supported")
    CUSTOM_ENCOUNTERS[int(number)] = (list(enemies), str(message))


def setup_encounter(
    number: int,
    party_ids: Sequence[int] = (1,),
    *,
    camera_origin: tuple[float, float] = (0, 0),
    flags: MutableMapping[int, int] | None = None,
    npc_origin: tuple[float, float] | None = None,
    enemy_sprites: Mapping[str, str] | None = None,
    rng: random.Random | None = None,
) -> EncounterLayout:
    """Port scr_encountersetup for positions, party layout and battle opening text.

    The GML uses global.char[] slots: for a standard party supply (1,),
    (1,2), or (1,2,3), and do not compress away an occupied later slot.
    `npc_origin`, used only by encounter 3, is in GML stage coordinates.
    Flags are mutable when 93 is used (original sets global.flag[426]).
    """
    if len(party_ids) > 3:
        raise ValueError("Only three active party members are supported")
    party = (list(party_ids) + [0, 0, 0])[:3]
    config = 1 if party[0] and not party[1] and not party[2] else (
        2 if party[0] and party[1] and not party[2] else 0
    )
    xx, yy = camera_origin
    hero = [[80, 50], [80, 130], [80, 210]]
    if config == 1:
        hero[0][1] = 140
    elif config == 2:
        hero[0][1], hero[1][1] = 100, 180

    data = SOURCE_ENCOUNTERS.get(number)
    if number in CUSTOM_ENCOUNTERS:
        active, message = CUSTOM_ENCOUNTERS[number]
        overrides = {}
    elif data is not None:
        active, overrides, message = data
        if message is None:
            message = "* It is known."
    else:
        active, overrides, message = FALLBACK_ENEMIES, {}, "* It is known."

    # 0 is special: no switch changes, so there is one enemy at (500,40).
    if number == 0:
        active = [DEFAULT_SLOTS[0]]

    for (slot, axis), val in overrides.items():
        hero[slot][0 if axis == "x" else 1] = val

    # Both special formations set the *entire* hero arrays, not individual slots.
    if number in (227, 228):
        krloc = [94, 50]
        suloc = [80, 122]
        raloc = [72, 200]
        if config == 1:
            krloc = [80, 122]
        elif config == 2:
            krloc, suloc = [94, 86], [80, 166]
        hero = [krloc, suloc, raloc]

    # Conditional original battle text, controlled by global.flag[500].
    flag500 = (flags or {}).get(500, 0)
    if number in (4, 21) and flag500 >= 1:
        subject = "Rudinn" if number == 4 else "Jigsawry"
        if flag500 == 2:
            message = f"* Assumedly another different {subject} appeared!"
        else:
            message = f"* A different {subject} from last time drew near!"

    # Original side effect: each encounter 93 rolls 0,1,2,3.
    if number == 93 and flags is not None:
        try:
            flags[426] = (rng or random).choice((0, 1, 2, 3))
        except TypeError as exc:
            raise TypeError("Encounter 93 requires mutable flags") from exc

    # Enemy entries are compact in this definition but must be expanded to
    # three slots for scr_battle. Every GML case used contiguous live slots.
    sprites = enemy_sprites or {}
    defs: list[EnemyDefinition] = []
    slots: list[EnemySpawn | None] = []
    resources: list[str | None] = []
    for obj, mtype, ex, ey in active:
        if mtype == 0:
            continue
        if number == 3 and npc_origin is not None:
            ex, ey = npc_origin
            ex -= xx
            ey -= yy
        defs.append(EnemyDefinition(obj, mtype, xx + ex, yy + ey))
        slots.append(EnemySpawn(mtype, xx + ex, yy + ey, sprites.get(obj, obj)))
        resources.append(obj)
    while len(slots) < 3:
        slots.append(None)
        resources.append(None)
    return EncounterLayout(
        number=number,
        enemy_definitions=defs,
        enemy_slots=slots,
        hero_positions=[(xx + hx, yy + hy) for hx, hy in hero],
        battle_message=message,
        camera_origin=camera_origin,
        resource_names=resources,
    )
