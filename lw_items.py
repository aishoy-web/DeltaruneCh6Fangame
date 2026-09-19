"""
Light World item data and helpers.

Based on DELTARUNE's Light World item scripts:
- scr_litemname
- scr_litemdesc
- scr_litemuseb
- scr_lweaponeq
- get_lw_dw_weapon_list

The UI should ask this module for item names/descriptions/weapon metadata,
while Game owns the mutable state and context-sensitive effects.
"""

LW_ITEM_NAMES = {
    1: "Hot Chocolate",
    2: "Pencil",
    3: "Bandage",
    4: "Bouquet",
    5: "Ball of Junk",
    6: "Halloween Pencil",
    7: "Lucky Pencil",
    8: "Egg",
    9: "Cards",
    10: "Box of Heart Candy",
    11: "Glass",
    12: "Eraser",
    13: "Mech. Pencil",
    14: "Wristwatch",
    15: "Holiday Pencil",
    16: "CactusNeedle",
    17: "BlackShard",
    18: "QuillPen",
    19: "Honey Toast",
    20: "Bread",
    21: "Seeds",
    22: "Pencil2",
    23: "Petal",
}

LW_ITEM_IDS_BY_NAME = {
    name: item_id
    for item_id, name in LW_ITEM_NAMES.items()
}


# Canonical equipment-name maps used by the STAT screen.
LW_WEAPON_NAMES = {
    item_id: LW_ITEM_NAMES[item_id]
    for item_id in (
        2, 6, 7, 12, 13, 15, 16, 17, 18, 22, 23
    )
}

LW_ARMOR_NAMES = {
    3: "Bandage",
    14: "Wristwatch",
}

# Light World ID -> Dark World ID + Light World strength.
LW_WEAPONS = {
    2:  {"dw_id": 1,  "strength": 1},
    6:  {"dw_id": 5,  "strength": 1},
    7:  {"dw_id": 8,  "strength": 1},
    12: {"dw_id": 14, "strength": 1},
    13: {"dw_id": 16, "strength": 1},
    16: {"dw_id": 23, "strength": 2},
    17: {"dw_id": 26, "strength": 16},
    15: {"dw_id": 50, "strength": 1},
    18: {"dw_id": 53, "strength": 1},
    22: {"dw_id": 30, "strength": 2},
    23: {"dw_id": 33, "strength": 0},
}

# Each list entry is one dialogue page.
# GameMaker's "&" line separators were converted to "\n".
LW_ITEM_DESCRIPTIONS = {
    1: [
        '* "Hot Chocolate" - Topped with home-made marshmallows '
        'in the shape of bunnies.'
    ],
    2: [
        '* "Pencil" - Weapon 1 AT\n'
        '* Mightier than a sword?\n'
        '* Maybe equal at best.'
    ],
    3: [
        '* "Bandage" - Heals 10 HP\n'
        '* It has cartoon characters on it.'
    ],
    4: [
        '* "Bouquet" - A bouquet of beautiful flowers in many colors.',
        '* Perhaps it could be offered to someone.',
    ],
    5: [
        '* "Ball of Junk" - A small ball of accumulated things in your pocket.'
    ],
    6: [
        '* "Halloween Pencil" - Weapon 1 AT\n'
        '* Orange with black bats on it.'
    ],
    7: [
        '* "Lucky Pencil" - Weapon 1 AT\n'
        '* Covered in green clovers and rainbows.'
    ],
    8: [
        '* "Egg" - Not too important, not too unimportant.'
    ],
    9: [
        '* "Cards" - The Jack of Spades, and the Rules Card.'
    ],
    10: [
        '* "Box of Heart Candy" - It\'s not yours. Will that stop you?'
    ],
    11: [
        '* There is a small shard of something in your pocket.',
        '* It feels like glass, but...',
    ],
    12: [
        '* "Eraser" - Weapon 1 AT\n'
        '* Pink, it bounces when thrown on the ground.'
    ],
    13: [
        '* "Mechanical Pencil" - 1 AT\n'
        '* It\'s tempting to click it repeatedly.'
    ],
    14: [
        '* "Wristwatch" - Armor 1 DF\n'
        '* Maybe an expensive antique.\n'
        '* Stuck before half past noon.'
    ],
    15: [
        '* "Holiday Pencil" - 1 AT\n'
        '* A festive candycane pencil.\n'
        '* Do not eat.'
    ],
    16: [
        '* "CactusNeedle" - 2 AT\n'
        '* Ouch! ... It\'s somewhat sentimental in a way.'
    ],
    17: [
        '* "BlackShard" - A small chip of extremely hard glass.\n'
        '* Oddly, it\'s nearly opaque.'
    ],
    18: [
        '* "QuillPen" - 1 AT\n'
        '* A pen fashioned from a white feather.'
    ],
    19: [
        '* "Honey Toast" - A food that a parent could eat.'
    ],
    20: [
        '* "Bread" - A loaf of bread. Tends to leave crumbs wherever it goes.'
    ],
    21: [
        '* "Seeds" - The seed of the golden flower.'
    ],
    22: [
        '* "Pencil2" - 2 AT\n'
        '* It\'s a No. 2 Pencil. ... that\n'
        'doesn\'t make it any stronger.'
    ],
    23: [
        '* "Petal" - 0 AT\n'
        '* A cyan colored petal. It\'s not\n'
        'a weapon, but it\'s nice.'
    ],
}

ITEM_ACTIONS = ("USE", "INFO", "DROP")

# Exact action-row cursor positions from obj_overworldc Draw,
# converted to the project's 320x240 logical UI coordinates.
ITEM_ACTION_CURSOR_POSITIONS = (
    (104, 184),  # USE
    (152, 184),  # INFO
    (209, 184),  # DROP
)


def normalize_lw_item_id(item):
    """Accept the new numeric representation plus legacy menu entries."""
    if isinstance(item, bool):
        return None

    if isinstance(item, int):
        return item if item in LW_ITEM_NAMES else None

    if isinstance(item, float) and item.is_integer():
        value = int(item)
        return value if value in LW_ITEM_NAMES else None

    if isinstance(item, dict):
        if "id" in item:
            return normalize_lw_item_id(item["id"])
        if "name" in item:
            return LW_ITEM_IDS_BY_NAME.get(str(item["name"]))

    if isinstance(item, str):
        stripped = item.strip()
        if stripped.isdigit():
            value = int(stripped)
            return value if value in LW_ITEM_NAMES else None
        return LW_ITEM_IDS_BY_NAME.get(stripped)

    return None


def get_lw_item_name(item):
    item_id = normalize_lw_item_id(item)
    if item_id is None:
        if isinstance(item, dict):
            return str(item.get("name", ""))
        return str(item)
    return LW_ITEM_NAMES.get(item_id, "")


def get_lw_item_description(item_id):
    item_id = normalize_lw_item_id(item_id)
    if item_id is None:
        return ["* Your eyesight became blurry."]
    return list(
        LW_ITEM_DESCRIPTIONS.get(
            item_id,
            ["* Your eyesight became blurry."],
        )
    )


def get_lw_weapon(item_id):
    item_id = normalize_lw_item_id(item_id)
    if item_id is None:
        return None
    return LW_WEAPONS.get(item_id)


def is_lw_weapon(item_id):
    return get_lw_weapon(item_id) is not None


def get_lw_weapon_strength(item_id):
    weapon = get_lw_weapon(item_id)
    if weapon is None:
        return 0
    return int(weapon["strength"])


def get_dw_weapon_id(item_id):
    weapon = get_lw_weapon(item_id)
    if weapon is None:
        return None
    return int(weapon["dw_id"])
