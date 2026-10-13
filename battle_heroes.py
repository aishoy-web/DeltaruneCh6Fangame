"""Shared obj_heroparent Create/Step port for four Dark World heroes.

Pure simulation: sprite identifiers are names rather than loaded images. Damage is
computed only when both stats are supplied by authentic party/monster setup.
Enemy event callbacks and scr_spell are kept as injectable boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor
from typing import TYPE_CHECKING, Callable, Mapping

if TYPE_CHECKING:
    from battle_combat import CombatActor, CombatEnemy, CombatState


def gml_round(value: float) -> int:
    """GameMaker's round-to-nearest convention for positive/negative damage."""
    return floor(value + .5) if value >= 0 else ceil(value - .5)


@dataclass(frozen=True)
class HeroProfile:
    character_id: int
    sprites: dict[str, str]
    attackframes: int = 3
    itemframes: int = 3
    defendframes: int = 1
    actframes: int = 7
    actreturnframes: int = 10
    spellframes: int = 10
    attackspeed: float = .5
    width: int = 34
    height: int = 37
    victoryframes: int | None = None  # Source uses sprite_get_number; assets not available.


def hero_profile(character_id: int, *, chapter: int = 6, encounter_no: int = 0,
                 weapon: int | None = None, flag_1311: bool = False,
                 sprite_frame_counts: Mapping[str, int] | None = None) -> HeroProfile:
    """obj_heroparent Create sprite/animation overrides without requiring assets."""
    if character_id not in (1, 2, 3, 4):
        raise ValueError(f"Unknown battle character ID: {character_id}")
    names = ('normal', 'idle', 'defend', 'hurt', 'attackready', 'attack', 'item',
             'itemready', 'spellready', 'spell', 'defeat', 'victory', 'actready', 'act')
    roots = {
        1: ('krisr_dark', 'krisb_idle', 'krisb_defend', 'krisb_hurt', 'krisb_attackready',
            'krisb_attack', 'krisb_item', 'krisb_itemready', 'krisb_actready', 'krisb_act',
            'krisb_defeat', 'krisb_victory', 'krisb_actready', 'krisb_act'),
        2: ('susier_dark', 'susieb_idle', 'susieb_defend', 'susieb_hurt', 'susieb_attackready',
            'susieb_attack', 'susieb_item', 'susieb_itemready', 'susieb_spellready',
            'susieb_spell', 'susieb_defeat', 'susieb_victory', 'susieb_actready', 'susieb_act'),
        3: ('ralsei_walk_right', 'ralsei_idle', 'ralsei_defend', 'ralsei_hurt_fixed',
            'ralsei_attackready', 'ralsei_attack', 'ralsei_item', 'ralsei_itemready',
            'ralsei_spellready', 'ralsei_spell', 'ralsei_defeat', 'ralsei_victory',
            'ralsei_actready', 'ralsei_act'),
        4: ('noelle_walk_right_dw', 'noelleb_idle', 'noelleb_defend', 'noelleb_hurt',
            'noelleb_attackready', 'noelleb_attack', 'noelleb_item', 'noelleb_itemready',
            'noelleb_spellready', 'noelleb_spell', 'noelleb_defeat', 'noelleb_victory',
            'noelleb_actready', 'noelleb_act'),
    }
    sprites = {key: 'spr_' + name for key, name in zip(names, roots[character_id])}
    params = {
        1: (6, 6, 5, 10, 68, 74),
        2: (5, 5, 5, 8, 70, 82),
        3: (6, 6, 7, 10, 52, 86),
        4: (4, 9, 0, 6, 52, 86),
    }
    atk, item, defend, spell, width, height = params[character_id]
    if character_id == 2:
        if weapon == 0:
            for key in ('idle', 'attackready', 'attack'):
                sprites[key] += '_unarmed'
        if chapter == 5 and encounter_no == 225:
            sprites.update(normal='spr_susier_dark_unhappy',
                           idle='spr_susieb_idle_unarmed_unhappy' if weapon == 0 else 'spr_susieb_idle_serious',
                           defend='spr_susieb_defend_unhappy', attack='spr_susieb_attack_serious',
                           item='spr_susieb_item_unhappy', itemready='spr_susieb_itemready_unhappy',
                           spellready='spr_susieb_spellready_unhappy', spell='spr_susieb_spell_unhappy')
    elif character_id == 3:
        if chapter == 5 and flag_1311:
            atk = 5
            for key, name in {
                'normal':'ralseir', 'idle':'ralseib_idle', 'defend':'ralseib_defend',
                'hurt':'ralsei_shock', 'attackready':'ralseib_attackready',
                'attack':'ralseib_attack', 'item':'ralseib_item',
                'itemready':'ralseib_itemready', 'spellready':'ralseib_spellready',
                'spell':'ralseib_spell', 'defeat':'ralseib_defeat',
                'victory':'ralseib_victory', 'actready':'ralseib_actready', 'act':'ralseib_act'
            }.items():
                sprites[key] = 'spr_' + name
        if chapter == 5 and encounter_no == 225:
            sprites.update(idle='spr_ralsei_idle_mad', defend='spr_ralsei_defend_serious',
                           hurt='spr_ralsei_kneel', attackready='spr_ralse_attackready_serious',
                           attack='spr_ralse_attack_serious', defeat='spr_ralsei_kneel')
    elif character_id == 4 and encounter_no == 73:
        sprites['idle'] = 'spr_noelle_shocked_dw'
    counts = sprite_frame_counts or {}
    frames = counts.get(sprites['victory'])
    return HeroProfile(character_id, sprites, atk, item, defend, 7, 10,
                       spell, .5, width, height, frames)


@dataclass(frozen=True)
class HeroHit:
    party_slot: int
    enemy_slot: int
    points: int
    damage: int | None
    remaining_hp: int | None
    defeated: bool
    # False for unknown attack/defense; do not imply a miss or deal zero.
    resolved: bool


@dataclass(slots=True)
class HeroCombatAnimation:
    actor: CombatActor
    profile: HeroProfile
    state: int = 0
    points: int = 0
    index: float = 0
    thissprite: str = ''
    siner: int = 0
    attacktimer: float = 0
    attacked: bool = False
    finishattacktimer: int = 0
    spelltimer: int = 0
    itemed: bool = False
    defendtimer: float = 0
    acttimer: float = 0
    act_init: bool = False
    victoryanim: float = 0
    hurt: bool = False
    hurttimer: int = 0
    hurtindex: float = 0
    poisonamount: int = 0
    poisontimer: int = 0
    force: bool = False
    darkentimer: int = 0
    pinkflashtimer: int = 0
    mercy: float = 0
    mercymax: float = 100
    mercyalpha: float = 0
    mercycon: bool = False
    last_hit: HeroHit | None = None

    def __post_init__(self):
        self.thissprite = self.profile.sprites['idle']

    def reset_turn(self):
        self.state = self.actor.state = 0
        self.attacktimer = self.actor.attacktimer = 0
        self.attacked = self.itemed = False
        self.finishattacktimer = self.spelltimer = 0
        self.acttimer = self.defendtimer = 0
        self.act_init = False
        self.force = False
        self.last_hit = None

    def step(self, battle: CombatState, *,
             resolve_attack: Callable[[CombatActor], HeroHit] | None = None,
             resolve_spell: Callable[[CombatActor], None] | None = None,
             on_sound: Callable[[str, float, CombatActor], None] | None = None):
        """obj_heroparent Step, per 60 Hz frame. Sprite rendering is separate."""
        a, slot, cid, p = self.actor, self.actor.slot, self.actor.character_id, self.profile
        self.state = a.state  # obj_attackpress/obj_spellphase sets this externally.
        self.points = a.points
        alive = a.hp is None or a.hp > 0
        if not alive:
            self.hurt = False
            self.hurttimer = 0
            self.thissprite, self.index = p.sprites['defeat'], 0
        else:
            if battle.myfight == 3 and battle.faceaction[slot] == 6 and self.state != 8:
                self.state = a.state = 6
            if self.state == 0 and not self.hurt:
                self.acttimer = 0
                face_sprite = {1:'attackready', 2:'spellready', 3:'itemready',
                               4:'defend', 6:'actready'}.get(battle.faceaction[slot], 'idle')
                self.thissprite = p.sprites[face_sprite]
                if face_sprite == 'defend':
                    self.index = self.defendtimer
                    if self.defendtimer < p.defendframes:
                        self.defendtimer += .5
                else:
                    self.defendtimer = 0
                    self.index = self.siner / 5
                self.siner += 1
            if self.state == 1 and not self.hurt:
                self.siner += 1
                if not self.attacked:
                    self.attacked = True
                    self.finishattacktimer = 11
                    if on_sound is not None:
                        pitch = {1:1.0, 2:.9, 3:1.15, 4:1.5}[cid]
                        on_sound('snd_laz_c', pitch, a)
                        if self.points == 150:
                            on_sound('snd_criticalswing', 1, a)
                self.thissprite = p.sprites['attack']
                self.index = min(self.attacktimer, p.attackframes)
                self.attacktimer += p.attackspeed
                a.attacktimer = self.attacktimer
                if self.force and self.index == p.attackframes:
                    self.reset_turn()
            if self.state in (2, 4) and not self.hurt:
                self.siner += 1
                if not self.itemed:
                    self.itemed = True
                    self.spelltimer = 16
                frames = p.spellframes if self.state == 2 else p.itemframes
                self.index = min(self.attacktimer, frames)
                if self.state == 2:
                    self.thissprite = p.sprites['spell']
                    if cid == 3 and battle.charspecial[slot] == 12:
                        self.thissprite = ('spr_ralseib_sing_ready' if battle.chapter == 5
                                           and p.sprites['spell'] == 'spr_ralseib_spell'
                                           else 'spr_ralsei_sing_ready')
                else:
                    self.thissprite = p.sprites['item']
                if any(e.active for e in battle.enemies):
                    self.attacktimer += .5
                else:
                    self.attacktimer = 0
                a.attacktimer = self.attacktimer
                if self.force and self.state == 2 and self.index == p.attackframes:
                    self.reset_turn()
            if self.state == 6:
                if not self.act_init:
                    self.act_init = True
                else:
                    if battle.myfight == 3:
                        self.acttimer = min(p.actframes, self.acttimer + .5)
                    else:
                        self.acttimer += .5
                    self.thissprite = p.sprites['act']
                    self.index = self.acttimer
                    if self.acttimer >= p.actreturnframes:
                        self.acttimer = 0
                        self.state = a.state = 0
                        battle.faceaction[slot] = 0
            else:
                self.act_init = False
            if self.state == 7:
                self.hurt = False
                self.hurttimer = 0
                self.thissprite = p.sprites['victory']
                self.index = self.victoryanim
                if p.victoryframes is None or self.victoryanim < p.victoryframes:
                    self.victoryanim += .334
                else:
                    self.thissprite, self.index = p.sprites['normal'], 0
            if self.hurt and self.state != 8 and a.hp is not None and a.hp > 0:
                self.hurtindex = min(2, self.hurttimer / 2)
                if battle.faceaction[slot] == 0:
                    battle.faceaction[slot] = 5
                if self.hurttimer > 15:
                    self.hurttimer = 0
                    self.hurt = False
                    if battle.faceaction[slot] == 5:
                        battle.faceaction[slot] = 0
                self.hurttimer += 1
            if self.state == 8:
                # State 8 uses externally supplied sprite/image frames.
                # The recovered ordinary battle actions do not enter it.
                pass
        if self.poisonamount > 0:
            self.poisontimer += 1
            if self.poisontimer >= 10:
                if a.hp is not None:
                    if a.hp > 1:
                        a.hp -= 1
                        self.poisonamount -= 1
                    else:
                        self.poisonamount = 0
                self.poisontimer = 0
        if self.finishattacktimer > 0:
            self.finishattacktimer -= 1
            if self.finishattacktimer == 0:
                battle.faceaction[slot] = 0
                if resolve_attack is not None:
                    self.last_hit = resolve_attack(a)
        if self.spelltimer > 0:
            self.spelltimer -= 1
            if self.spelltimer == 0:
                if p.spellframes > 0:
                    battle.faceaction[slot] = 0
                if any(e.active for e in battle.enemies) and resolve_spell is not None:
                    resolve_spell(a)
                self.state = a.state = 0
                self.attacktimer = a.attacktimer = 0
                self.itemed = False


def calculate_attack_damage(attack: int | None, points: int,
                            defense: int | None, monster_type: int,
                            *, trashy_trio_present: bool = False) -> int | None:
    """Recovered GML damage equation, with type-19/trashy-trio modifiers.

    No placeholder damage is generated when an equipment/monster stat is unknown.
    """
    if attack is None or defense is None:
        return None
    damage = gml_round((attack * points / 20) - (defense * 3))
    if monster_type == 19:
        damage = ceil(damage * .3)
    if trashy_trio_present:
        damage = ceil(damage * .1)
    return max(0, damage)
