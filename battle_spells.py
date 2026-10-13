"""Recovered scr_spell(arg0, arg1) effects for the Chapter 6 battle controller.

The source makes an important distinction between instant effects and spawned
GameMaker animation instances. This module applies only source-confirmed instant
changes; animated effects are emitted as requests for later object ports.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from random import Random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from battle_combat import BattleCombatController


@dataclass(frozen=True, slots=True)
class SpellAnimationRequest:
    object_name: str
    caster_slot: int
    target_slot: int | None
    damage: int | None = None
    heal: int | None = None
    delay: int = 0
    extra: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class SpellOutcome:
    code: int
    caster_slot: int
    target_slot: int
    spell_delay: int
    direct_damage: int | None = None
    heals: tuple[tuple[int, int], ...] = ()
    animations: tuple[SpellAnimationRequest, ...] = ()
    unresolved: tuple[str, ...] = ()


# scr_healitemspell and scr_healallitemspell use the same modifier routine.
SINGLE_HEALS = {
    201: 120, 205: 20, 208: 70, 209: 50, 210: 4, 212: None,
    213: None, 214: 500, 215: 50, 216: 80, 218: 10, 219: 10,
    220: 10, 221: 10, 222: 60, 223: 120, 224: 100, 226: None,
    234: 100, 236: 20, 237: 80, 239: 140, 241: 130,
    242: 180, 243: 80, 260: None, 261: 115, 262: None,
    266: 200, 267: None, 268: None, 269: None,
}
ALL_HEALS = {206: 160, 207: None, 211: 70, 225: 30, 238: 100,
             240: 200, 264: 200, 265: 160, 270: 80}


def _valid_actor(state, slot):
    return next((a for a in state.actors if a.slot == slot), None)


def scr_spell(controller: "BattleCombatController", code: int, caster_slot: int,
              *, rng: Random | None = None) -> SpellOutcome:
    """Apply scr_spell. ``star`` refers to an enemy or party *slot*.

    Source effects involving `obj_icespell`, `obj_rudebuster_anim`,
    `obj_spell_snowgrave`, `obj_spell_mist`, `obj_spell_scythemare`,
    `obj_spell_revivesong`, etc. are never converted into instantaneous hits.
    The pending requests can be completed once their respective object source
    scripts become available.
    """
    s = controller.state
    if not (0 <= caster_slot < 3) or s.party_ids[caster_slot] == 0:
        raise ValueError("Spell caster must occupy an active party slot")
    code = int(code)
    star = s.chartarget[caster_slot]
    s.spelldelay = 10
    animations: list[SpellAnimationRequest] = []
    heals: list[tuple[int, int]] = []
    pending: list[str] = []
    direct_damage: int | None = None

    def magic(slot=caster_slot):
        return s.battlemag[slot] if 0 <= slot < 3 else None

    def attack():
        return s.battleat[caster_slot]

    def armor(cid):
        return 36 in controller.equipped_armors.get(cid, ())

    def mod(value):
        # scr_heal_amount_modify_by_equipment not supplied. Use a callback if
        # provided; otherwise the source's unmodified value is the base case.
        cb = controller.on_spell_heal_modifier
        return cb(value, s, caster_slot) if cb is not None else value

    def heal(slot, amount, *, modified=True):
        actor = _valid_actor(s, slot)
        if actor is None:
            return
        value = ceil(mod(amount) if modified else amount)
        heals.append((slot, value))
        controller._heal_character(actor, value)
        if actor.hp is None or actor.max_hp is None:
            pending.append(f"scr_heal:slot={slot}:unknown_HP")
        actor.tu += 1

    def active_target():
        nonlocal star
        current = next((e for e in s.enemies if e.slot == star and e.active), None)
        if current is None:
            if controller.on_spell_retarget is not None:
                controller.on_spell_retarget(s, caster_slot)
                star = s.chartarget[caster_slot]
                current = next((e for e in s.enemies if e.slot == star and e.active), None)
            else:
                # scr_retarget_spell has yet to be provided.
                pending.append('scr_retarget_spell')
        return current

    def emit(object_name, target, *, damage=None, heal_amount=None, delay=0, **extras):
        request = SpellAnimationRequest(object_name, caster_slot, target, damage,
                                        heal_amount, delay, tuple(extras.items()))
        animations.append(request)
        controller._emit_spell_animation(request)

    if code == 1:  # RUDE BUSTER (source's instantaneous scr_damage_enemy)
        enemy = active_target()
        if enemy is not None:
            if attack() is not None and enemy.defense is not None:
                damage = ceil(attack() * 10 - enemy.defense * 3)
                if s.automiss[star]:
                    damage = 0
                direct_damage = controller.damage_enemy(star, damage, caster_slot)
                # scr_spell case 1 sets `dm.delay = 8` after calling
                # scr_damage_enemy; dm is the new damage-writer instance.
                if direct_damage is not None and s.damage_writer_events:
                    s.damage_writer_events[-1].delay = 8
                if direct_damage is None:
                    pending.append('scr_damage_enemy:unknown_HP')
                emit('obj_basicattack', star, damage=direct_damage)
            else:
                pending.append('scr_damage_enemy:unknown_attack_or_defense')
        s.spelldelay = 30
    elif code == 2:  # HEAL PRAYER
        if magic() is not None:
            heal(star, magic() * (6 if armor(3) else 5))
        else:
            pending.append('HEAL_PRAYER:unknown_magic')
        s.spelldelay = 15
    elif code == 3:  # PACIFY
        enemy = active_target()
        if enemy is not None:
            if enemy.status == 1:
                if enemy.monster_type not in (19, 3, 52, 43):
                    emit('obj_pacifyspell', star, delay=20,
                         vertical_offset=-60 if enemy.monster_type == 33 else 0)
                    controller.defeat_enemy(star, outcome=3, call_user10=True)
                else:
                    enemy.pacifycon = 1
                    if enemy.monster_type == 52:
                        emit('obj_pacifyspell', star, delay=20)
                    # The GML writes 999 here, then unconditionally 20 below.
            else:
                if enemy.monster_type == 52:
                    enemy.pacifycon = -2
                emit('obj_pacifyspell', star, delay=20, fail=True)
        s.spelldelay = 20
    elif code in (4, 5):  # RUDE BUSTER / RED BUSTER animations own their damage
        enemy = active_target()
        s.spelldelay = 30
        if enemy is not None:
            if magic() is None or attack() is None or enemy.defense is None:
                pending.append(f'obj_rudebuster_anim:unknown_stats:spell={code}')
            else:
                if code == 4:
                    amount = ceil(magic() * (5.5 if armor(2) else 5) +
                                  attack() * (12 if armor(2) else 11) - enemy.defense * 3)
                else:
                    amount = ceil(magic() * 6 + attack() * 13 - enemy.defense * 6)
                if s.automiss[star]:
                    amount = 0
                emit('obj_rudebuster_anim', star, damage=amount, red=int(code == 5))
                s.spelldelay = 70
    elif code == 6:  # DUAL HEAL
        if magic() is not None:
            for slot in range(3):
                heal(slot, magic() * 5.5)
        else:
            pending.append('DUAL_HEAL:unknown_magic')
        s.spelldelay = 15
    elif code == 8:  # SLEEPMIST effect lives in obj_spell_mist
        alive = [e for e in s.enemies if e.active]
        for n, enemy in enumerate(alive):
            emit('obj_spell_mist', enemy.slot, delay=n * 10)
        s.spelldelay = 20 + len(alive) * 10
    elif code == 9:  # ICESHOCK animation owns damage/freezing
        enemy = active_target()
        s.spelldelay = 30
        if enemy is not None:
            controller.flags[925] = controller.flags.get(925, 0) + 1
            if magic() is not None:
                roll = (rng or controller.spell_rng).random() * 10
                amount = ceil(max(1, min(999, magic() - 10)) * 30 + 90 + roll)
                emit('obj_icespell', star, damage=amount)
                s.spelldelay = 40
            else:
                pending.append('obj_icespell:unknown_magic')
    elif code == 10:  # SNOWGRAVE delayed/AOE animation
        if any(e.active for e in s.enemies):
            if magic() is not None:
                emit('obj_spell_snowgrave', None, damage=ceil(magic() * 40 + 600))
                s.spelldelay = 140
            else:
                pending.append('obj_spell_snowgrave:unknown_magic')
        else:
            s.spelldelay = 30
    elif code == 11:  # Chapter 5 HEAL uses battlemag[1] explicitly
        controller.flags[20] = 1
        controller.flags[1045] = min(15, controller.flags.get(1045, 0) + 1)
        count = controller.flags[1045]
        if magic(1) is not None:
            m = magic(1)
            multiplier = 7 if controller.flags.get(852, 0) == 1 else 5
            base = m * multiplier + 15
            if armor(2):
                base *= 1.2
            amount = ceil(mod(base + 2 * count))
            actor = _valid_actor(s, star)
            if actor is not None and actor.hp is not None and actor.hp < 0:
                # GML repeat(healnum) raises the amount until healing passes 0,
                # up to one further healnum amount.
                extra = 0
                for _ in range(max(0, amount)):
                    if amount + extra + actor.hp > 0 or extra >= amount:
                        break
                    extra += 1
                amount += extra
            heal(star, amount, modified=False)
        else:
            pending.append('HEAL:unknown_party_slot_1_magic')
        s.spelldelay = 15
        pending.append('scr_spellmenu_setup')
    elif code == 12:  # REVIVESONG animation applies healing later
        actor = _valid_actor(s, star)
        if actor is not None and actor.hp is not None and magic() is not None:
            raw = ((-actor.hp + magic() * (9 if armor(3) else 7.5))
                   if actor.hp <= 0 else magic() * (12 if armor(3) else 10))
            emit('obj_spell_revivesong', star, heal_amount=ceil(mod(raw)))
        else:
            pending.append('obj_spell_revivesong:unknown_HP_or_magic')
        s.spelldelay = 75
    elif code == 13:  # SCYTHEMARE animation owns PACIFY/attack effects
        alive = [e for e in s.enemies if e.active]
        for n, enemy in enumerate(alive):
            emit('obj_spell_scythemare', enemy.slot, delay=n * 10,
                 num=n, laugh=bool(n == 0))
        s.spelldelay = 64 + len(alive) * 10
    elif code == 100:  # SPARE
        enemy = active_target()
        if enemy is not None:
            if enemy.mercy is not None and enemy.mercy >= 100:
                if enemy.monster_type not in (3, 52):
                    controller.defeat_enemy(star, outcome=2, call_user10=True)
                else:
                    enemy.sparecon = 1
            else:
                if controller.on_spell_mercy_add is not None:
                    controller.on_spell_mercy_add(enemy, enemy.spare_point)
                elif enemy.mercy is not None:
                    enemy.mercy += enemy.spare_point
                else:
                    pending.append('scr_mercyadd:unknown_mercy')
                s.monster_slots[enemy.slot].sync_from_enemy(enemy)
                emit('obj_pacifyspell', star, fail=True, flashcolor='yellow')
        s.spelldelay = 0
    elif code in SINGLE_HEALS:
        base = SINGLE_HEALS[code]
        cid = s.party_ids[star] if 0 <= star < 3 else 0
        if code == 212:
            base = {1: 20, 2: 80, 3: 50, 4: 30}.get(cid)
        elif code == 213:
            base = {1: 80, 2: 20, 3: 50, 4: 70}.get(cid)
        elif code == 226:
            base = 100 if cid == 1 else 90
        elif code == 260:
            base = 400 if cid == 1 else 40
        elif code == 262:
            base = 155 if cid == 4 else 160
        elif code == 267:
            base = 200 if cid == 1 else 100
        elif code == 268:
            base = 200 if cid == 2 else 100
        elif code == 269:
            base = 200 if cid == 3 else 50
        if base is not None:
            heal(star, base)
            if code == 262 and cid == 4:
                heal(0, 5)
    elif code in ALL_HEALS:
        base = ALL_HEALS[code]
        if code == 207:
            base = (180 if s.chapter == 5 else 80 if s.chapter == 1 else 140)
        for slot in range(3):
            heal(slot, base)
    elif code == 202:  # REVIVEMINT
        actor = _valid_actor(s, star)
        if actor is not None and actor.hp is not None and actor.max_hp is not None:
            value = (actor.max_hp + abs(actor.hp) if actor.hp <= 0
                     else ceil(mod(actor.max_hp / 2)))
            heal(star, value, modified=False)
        else:
            pending.append('REVIVEMINT:unknown_HP')
    elif code in (230, 231):  # REVIVEDUST and REVIVEBRIGHT
        for actor in s.actors:
            value = 10 if code == 230 else 50
            if actor.hp is not None and actor.max_hp is not None and actor.hp <= 0:
                value = (ceil(actor.max_hp / 4) + abs(actor.hp)) if code == 230 else 999
            heal(actor.slot, value)
    elif code == 232:  # S.POISON
        actor = _valid_actor(s, star)
        if actor is not None and actor.hero_animation is not None:
            actor.hero_animation.poisonamount = 60
        heal(star, 40)
    elif code == 263:  # BITTERTEAR
        actor = _valid_actor(s, star)
        if actor is not None and actor.hp is not None and actor.max_hp is not None:
            heal(star, ceil(mod(actor.max_hp) + abs(actor.hp)), modified=False)
        else:
            pending.append('BITTERTEAR:unknown_HP')
    # GML has no default effect for other IDs (including 0, 200, 203, 204,
    # 217, 227..229, 233, 235). Note that narration is in scr_spelltext.

    result = SpellOutcome(code, caster_slot, star, s.spelldelay, direct_damage,
                          tuple(heals), tuple(animations), tuple(pending))
    s.spell_effect_outcomes.append(result)
    return result
