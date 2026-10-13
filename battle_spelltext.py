"""Port of scr_spelltext: exact source message templates and recovered branches.

The source uses GameMaker localization and battle-writer control codes; templates
are preserved in SOURCE_TEMPLATES and ``messages`` retains their control codes.
Renderers can use ``battle_text_to_display``. Spell effects not present in this
script are NOT inferred; the caller can register the original event callbacks.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
import re


SOURCE_TEMPLATES: dict[int, str] = {
    1: '\\* ~1 cast RUDE BUSTER!/%',
    2: '\\* ~1 cast HEAL PRAYER!/%',
    4: '\\* ~1 used RUDE BUSTER!/%',
    5: '\\* ~1 used RED BUSTER!/%',
    6: '\\* ~1 cast DUAL HEAL!/%',
    8: '\\* ~1 cast SLEEPMIST!/%',
    9: '\\* ~1 cast ICESHOCK!/%',
    10: '\\* ~1 cast SNOWGRAVE!/%',
    11: '\\* ~1 cast HEAL!/%',
    12: '\\* ~1 cast REVIVESONG!/%',
    13: '\\* ~1 cast SCYTHEMARE!/%',
    201: '\\* ~1 used the DARKER CANDY!/%',
    202: '\\* ~1 used the REVIVEMINT!/%',
    205: '\\* ~1 used the BROKEN CAKE!/%',
    206: '\\* ~1 used the TOPCAKE!/%',
    207: '\\* ~1 used the SPINCAKE!/%',
    208: '\\* ~1 used the DARKBURGER!/%',
    209: '\\* ~1 used the LANCERCOOKIE!/%',
    210: '\\* ~1 used the GIGASALAD!/%',
    211: '\\* ~1 used the CLUBS SANDWICH!/%',
    212: '\\* ~1 used the HEARTS DONUT!/%',
    213: '\\* ~1 used the CHOCO DIAMOND!/%',
    214: '\\* ~1 used the FAV SANDWICH!/%',
    215: '\\* ~1 used the ROUXLS ROUX!/%',
    216: '\\* ~1 used the CD BAGEL!/%',
    217: '\\* ~1 used the CLOTHESDOLL!/',
    222: '\\* ~1 used the DD-BURGER!/%',
    223: '\\* ~1 used the LIGHTCANDY!/%',
    224: '\\* ~1 used the BUTJUICE!/%',
    225: '\\* ~1 used the SPAGHETTICODE!/%',
    226: '\\* ~1 used the JAVACOOKIE!/%',
    227: '\\* ~1 used the TENSIONBIT!&\\* Tension raised up earlier./%',
    228: '\\* ~1 used the TENSIONGEM!/%',
    229: '\\* ~1 used the TENSIONMAX!/%',
    230: '\\* ~1 used the REVIVEDUST!/%',
    231: '\\* ~1 used the REVIVEBRIGHT!/%',
    232: '\\* ~1 administered S.POISON!/%',
    233: '\\* ~1 admired DOGDOLLAR!/%',
    234: '\\* ~1 used the TVDINNER!/%',
    235: '\\* ~1 used the PIPIS!/%',
    236: '\\* ~1 used the FLATSODA!/%',
    237: '\\* ~1 used the TVSLOP!/%',
    238: '\\* ~1 used the EXECBUFFET!/%',
    239: '\\* ~1 used the DELUXEDINNER!/%',
    240: '\\* ~1 used the PUNCHBOWL!/%',
    241: '\\* ~1 used the FLAVIGNE!/%',
    242: '\\* ~1 used the GREENTEA!/%',
    243: '\\* ~1 used the ORANGEJUICE!/%',
    260: '\\* ~1 used the ANCIENTSWEET!/%',
    261: '\\* ~1 used the RHAPSOTEA!/%',
    262: '\\* ~1 used the SCARLIXIR!/%',
    263: '\\* ~1 used the BITTERTEAR!/%',
    264: '\\* ~1 used the SCHADENBROT!/%',
    265: '\\* ~1 used the TREECAKE!/%',
    266: '\\* ~1 used the S.POTION!/%',
    267: '\\* ~1 used the RAW MOON!/%',
    268: '\\* ~1 used the PHANTA!/%',
    269: '\\* ~1 used the FLOWERYSODA!/%',
    270: '\\* ~1 used the SHIKACOLA!/%',
}


@dataclass(frozen=True, slots=True)
class SpellTextResult:
    code: int
    caster_slot: int
    target_slot: int
    messages: tuple[str, ...]
    text_id: int | None = None
    pending_effects: tuple[str, ...] = ()


def battle_text_to_display(message: str) -> str:
    """Strip known GML writer control sequences for the temporary Tk HUD."""
    message = re.sub(r"\\+c[A-Z]", "", message)
    message = re.sub(r"\^[0-9]+", "", message)
    message = message.replace("\\*", "*").replace("\\`", "`")
    message = message.replace("&", "\n").replace("/%", "").replace("/", "")
    return message


def _render(template: str, actor: str, monster: str = "") -> str:
    return template.replace("\\~1", "~1").replace("\\~2", "~2").replace("~1", actor).replace("~2", monster)


def scr_spelltext(code: int, caster_slot: int, state, *,
                  on_retarget: Callable | None = None,
                  on_text_id: Callable | None = None,
                  on_item_shift: Callable | None = None,
                  on_mercy_add: Callable | None = None) -> SpellTextResult:
    """scr_spelltext(arg0, arg1): narration, PACIFY/SPARE checks, and item specials.

    ``star`` is captured *before* scr_retarget_spell, just like the GML.
    Callbacks receive (state, caster_slot), (text_id, state, caster_slot),
    (item_index, 0), and (enemy, mercy_amount), respectively.
    """
    slot = int(caster_slot)
    if not 0 <= slot < 3 or state.party_ids[slot] == 0:
        raise ValueError(f"Cannot cast from empty party slot {slot}")
    code = int(code)
    target = state.chartarget[slot]
    actor = next((a for a in state.actors if a.slot == slot), None)
    name = actor.name if actor is not None else f"Character {state.party_ids[slot]}"
    enemy = next((e for e in state.enemies if e.slot == target and e.active), None)
    enemy_name = enemy.name if enemy is not None else " "
    pending: list[str] = []
    messages: list[str] = []
    text_id = None

    if code in (0,):
        pass
    elif code in (3, 100):
        if on_retarget is not None:
            on_retarget(state, slot)
        else:
            pending.append("scr_retarget_spell")
        if code == 3:
            msg = f"\\* {name} cast PACIFY!/%"
            if enemy is not None and enemy.status != 1:
                msg = (f"\\* {name} cast PACIFY^1!&\\* But the enemy wasn't "
                       r"\cBTIRED\cW" + ".../%")
                if enemy.mercy is not None and enemy.mercy >= 100:
                    msg = (f"\\* {name} cast PACIFY^1!&\\* But the foe wasn't "
                           r"\cBTIRED\cW" + r"... try \cYSPARING\cW!/%")
            messages.append(msg)
        else:
            # Source's Shinobeetle special is evaluated before checking mercy.
            for foe in state.enemies:
                if (foe.active and foe.object_name == "obj_shinobeetle_enemy"
                        and sum(int(e.active) for e in state.enemies) == 1):
                    if not getattr(foe, "alone", False):
                        foe.alone = True
                        if on_mercy_add is not None:
                            on_mercy_add(foe, 100)
                        else:
                            pending.append("scr_mercyadd:shinobeetle:100")
            msg = f"\\* {name} spared {enemy_name}!/%"
            if enemy is not None and (enemy.mercy is None or enemy.mercy < 100):
                msg = (f"\\* {name} spared {enemy_name}^2!&"
                       r"\* But MERCY was not 100\`%!/%")
                if enemy.status == 1:
                    msg = (f"\\* {name} spared {enemy_name}^2!&"
                           r"\* But MERCY was not 100\`%!/")
                    if 3 in state.party_ids:
                        messages.append(msg)
                        messages.append(r"\* (Try using Ralsei's \cBPACIFY\cW!)/%")
                    elif 4 in state.party_ids:
                        messages.append(msg)
                        messages.append(r"\* (Try using Noelle's \cBSLEEPMIST\cW!)/%")
                    else:
                        messages.append(msg)
                        messages.append(r"\* (Try using \cBACTs\cW!)/%")
                else:
                    messages.append(msg)
            else:
                messages.append(msg)
    elif code == 203:
        messages.extend([f"\\* {name} used the GLOWSHARD!/", r"\* But nothing happened.../%"])
        selected = [e for e in state.enemies if e.active and e.monster_type == 5]
        if selected:
            for foe in selected:
                foe.mercy = 200  # GML global.mercymod[] = 200, not scr_mercyadd.
                state.monster_slots[foe.slot].sync_from_enemy(foe)
            item_slot = state.bmenucoord[4][slot]
            if on_item_shift is not None:
                on_item_shift(item_slot, 0)
            else:
                pending.append(f"scr_itemshift:{item_slot}:0")
            messages[1] = "".join(f"\\* {e.name} became enraptured!&" for e in selected) + "/"
            messages.append(r"\* The GLOWSHARD disappeared!/%")
    elif code == 204:
        messages.extend([f"\\* {name} read the MANUAL!/", r"\* But nothing happened.../%"])
        outcomes = []
        for foe in state.enemies:
            if not foe.active:
                continue
            if foe.monster_type == 5:
                foe.status, foe.tired, foe.comment = 1, True, "(Tired)"
                outcomes.append(f"\\* {foe.name} was " + r"\cBbored to tears\cW" + "!&")
            elif foe.monster_type == 6:
                outcomes.append(f"\\* {foe.name} listened politely!&")
            elif foe.monster_type in (7, 16):
                foe.battlecancel = 1
                if not getattr(foe, "manual", False):
                    foe.manual = True
                    if on_mercy_add is not None:
                        on_mercy_add(foe, 50)
                    else:
                        pending.append(f"scr_mercyadd:{foe.slot}:50")
                outcomes.append(f"\\* {foe.name} became sentimental!&")
            state.monster_slots[foe.slot].sync_from_enemy(foe)
        if outcomes:
            messages[1] = "".join(outcomes) + "/%"
    elif 218 <= code <= 221:
        text_id = 1463
        if on_text_id is not None:
            other = on_text_id(1463, state, slot)
            if isinstance(other, str):
                messages.append(other)
            elif isinstance(other, (tuple, list)):
                messages.extend(str(line) for line in other)
        else:
            pending.append("scr_text:1463")
    elif code in SOURCE_TEMPLATES:
        messages.append(_render(SOURCE_TEMPLATES[code], name, enemy_name))
        if code == 217:
            messages.append(r"\* ... but nothing happened!/%")
    # No default in the original switch. Leave global.msg unchanged for unknown IDs.
    return SpellTextResult(code, slot, target, tuple(messages), text_id,
                           tuple(pending))
