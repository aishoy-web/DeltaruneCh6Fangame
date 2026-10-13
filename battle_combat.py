"""Chapter 6 combat-controller foundation.

Ported from obj_battlecontroller Create, common Step menu/navigation and
victory branches, Alarm[2] and the normal Draw-event interface.

Monster reset, instance creation and end-of-turn cleanup are ported.
Enemy User events, scr_heal modifiers, action execution, and AI require
external hooks; no enemy HP, damage, spells, or ACT outcomes are fabricated.
scr_attackphase, scr_nextact, and scr_act_simul select the real
resolution phases; battle_phases handles recovered attack-press and
spell-phase timing without inventing missing damage or spell effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from math import floor, ceil
from random import Random

from encounter_setup import setup_encounter
from battle_phases import AttackPressPhase, SpellPhase
from battle_spelltext import scr_spelltext
from battle_spells import scr_spell, SpellOutcome, SpellAnimationRequest
from battle_effects import DamageWriterEvent, RudeBusterAnimation, RudeBusterBolt
from battle_heroes import HeroCombatAnimation, HeroHit, hero_profile, calculate_attack_damage, gml_round

from battle_monsters import (
    MonsterHooks, MonsterSlotState, monster_population,
    scr_monster_makeinstance, scr_monster_statreset, scr_monsterdefeat,
)


CHAR_NAMES = {1: "Kris", 2: "Susie", 3: "Ralsei", 4: "Noelle"}
CHAR_COLORS = {1: "#00ffff", 2: "#ff00ff", 3: "#00ff00", 4: "#ffff00"}
MENU_COMMANDS = ("FIGHT", "ACT", "ITEM", "SPARE", "DEFEND")
TARGET_ENEMY_MENUS = (1, 3, 11, 12, 13)
TARGET_ALLY_MENUS = (7, 8)
TARGET_MENUS = TARGET_ENEMY_MENUS + TARGET_ALLY_MENUS
PAGE_MENUS = (2, 4, 9)


@dataclass(frozen=True, slots=True)
class CombatOption:
    """Registered spell, ACT, or item (separate from Light World items)."""
    name: str
    code: int | str = 0
    description: str = ""
    tp_cost: float = 0
    target: int = 2  # 0=none, 1=ally, 2=enemy, 3=special enemy
    required_character_ids: tuple[int, ...] = ()
    simultaneous: bool = False  # global.actsimul[enemy][ACT choice] when registered


@dataclass(slots=True)
class CombatActor:
    slot: int
    character_id: int
    x: float
    y: float
    name: str
    attack: int | None = None
    defense: int | None = None
    magic: int | None = None
    hp: int | None = None
    max_hp: int | None = None
    can_move: bool = True
    can_target: bool = True
    dead: bool = False
    state: int = 0
    face_action: int = 0
    tu: int = 0
    points: int = 0
    attacktimer: int = 0
    is_auto_susie: bool = False
    visible: bool = True  # obj_rudebuster_anim hides Susie until frame 28
    # obj_heroparent Step/Draw keeps animation independently of the action menu.
    hero_animation: HeroCombatAnimation | None = None


@dataclass(slots=True)
class CombatEnemy:
    slot: int
    object_name: str
    monster_type: int
    x: float
    y: float
    name: str
    hp: int | None = None
    max_hp: int | None = None
    mercy: float | None = None
    mercy_max: float = 100.0
    tired: bool = False
    cant_spare: bool = False
    first_strike: bool = False
    active: bool = True
    # User[12] / User[15] are the source of stats: metadata is not a stat.
    stats_loaded: bool = False
    attack: int | None = None
    defense: int | None = None
    gold: int = 0
    exp: int = 0
    spare_point: int = 0
    hit_target: int = 0
    comment: str = " "
    attack_name: str = " "
    status: int = 0
    attacked: int = 0
    talked: int = 0
    acting: int = 0
    actingsus: int = 0
    actingral: int = 0
    actingnoe: int = 0
    # scr_nextact and scr_act_simul write these on monster instances.
    actcon: int = 0
    actconsus: int = 0
    actconral: int = 0
    actconnoe: int = 0
    simulorderkri: int = -1
    simulordersus: int = -1
    simulorderral: int = -1
    simulordernoe: int = -1
    simultotal: int = 0
    battlecancel: int = 0
    fatal: int = 0
    pacifycon: int = 0
    sparecon: int = 0
    manual: bool = False
    alone: bool = False
    # A chained encounter enters from camera x + 800 over ten frames.
    entrance_target_x: float | None = None
    entrance_target_y: float | None = None
    entrance_frames: int = 0
    # obj_monsterparent response fields set by scr_damage_enemy.
    state: int = 0
    shakex: int = 0
    hurttimer: int = 0
    hurtamt: int = 0
    candodge: int = 0
    dodgetimer: int = 0
    # obj_yellow_enemy intercept values, only when that object is present.
    blockcon: int = 0
    blocktimer: int = 0
    hurtsprite: str | None = None
    back: int = 0  # obj_trashy_trio RUDE BUSTER block timer


@dataclass(frozen=True, slots=True)
class QueuedAction:
    party_slot: int
    kind: str
    target_slot: int | None = None
    option: CombatOption | None = None
    item_slot: int | None = None


@dataclass(slots=True)
class CombatState:
    encounter_no: int
    chapter: int
    party_ids: tuple[int, int, int]
    battle_message: str
    actors: list[CombatActor]
    enemies: list[CombatEnemy]
    monster_slots: list[MonsterSlotState] = field(default_factory=lambda: [MonsterSlotState(i) for i in range(3)])
    # GameMaker global fields, retained under their GML names.
    darkzone: int = 1
    fighting: int = 1
    battleend: int = 0
    myfight: int = 0
    mnfight: int = 0
    bmenuno: int = 0
    charturn: int = 0
    currentactingchar: int = 0
    attacking: int = 0
    acting: int = 0
    tension: float = 0.0
    maxtension: float = 100.0
    tensionselect: float = 0.0
    spelldelay: int = 10
    turntimer: int = 120
    victory: int = 0
    victoried: int = 0
    skipvictory: int = 0
    victortimer: int = 0
    victory_message: str = ""
    victory_message_dismissed: bool = False
    fight_return_timer: int = 1
    messagepriority: int = -1
    attackpriority: int = -1
    hidemercy: bool = False
    shareitemcon: int = 0
    hidebattleui: bool = False
    itempage: int = 0
    spellpage: int = 0
    # Below are in the original GML 640x480 coordinate system.
    bp: int = 0
    bpy: int = 152
    tp: int = 0
    tpy: int = 50
    intro: int = 1
    reset: int = 0
    timeron: int = 1
    noreturn: int = 0
    fc: int = 0
    fe: int = 0
    typer: int = 4
    battletyper: int = 4
    chartotal: int = 0
    charpos: list[int] = field(default_factory=lambda: [-1] * 4)
    havechar: list[int] = field(default_factory=lambda: [0] * 4)
    charcond: list[int] = field(default_factory=lambda: [0] * 3)
    automiss: list[int] = field(default_factory=lambda: [0] * 3)
    charmove: list[int] = field(default_factory=lambda: [0] * 3)
    charcantarget: list[int] = field(default_factory=lambda: [0] * 3)
    chardead: list[int] = field(default_factory=lambda: [0] * 3)
    battleat: list[int | None] = field(default_factory=lambda: [None] * 3)
    battledf: list[int | None] = field(default_factory=lambda: [None] * 3)
    battlemag: list[int | None] = field(default_factory=lambda: [None] * 3)
    battleactcount: list[int] = field(default_factory=lambda: [0] * 3)
    monsterattackname: list[str] = field(default_factory=lambda: [" "] * 3)
    acting_choice: list[int] = field(default_factory=lambda: [0] * 3)
    charaction: list[int] = field(default_factory=lambda: [0] * 3)
    charspecial: list[int] = field(default_factory=lambda: [0] * 3)
    chartarget: list[int] = field(default_factory=lambda: [0] * 3)
    faceaction: list[int] = field(default_factory=lambda: [0] * 3)
    rembmenuno: list[int] = field(default_factory=lambda: [0] * 3)
    targeted: list[int] = field(default_factory=lambda: [0] * 3)
    hittarget: list[int] = field(default_factory=lambda: [0] * 3)
    acting_flags: list[int] = field(default_factory=lambda: [0] * 3)
    actingsingle: list[int] = field(default_factory=lambda: [0] * 3)
    actingsimul: list[int] = field(default_factory=lambda: [0] * 3)
    actingtarget: list[int] = field(default_factory=lambda: [0] * 3)
    susie_slot: int | None = None
    pending_heals: list[tuple[int, int]] = field(default_factory=list)
    awaiting_wincombat: bool = False
    bmenucoord: list[list[int]] = field(default_factory=lambda: [[0] * 20 for _ in range(20)])
    # Original tempitem[item_slot][party_slot] and temptension[party_slot].
    tempitem: list[list[int]] = field(default_factory=lambda: [[0] * 3 for _ in range(13)])
    temptension: list[float] = field(default_factory=lambda: [0.0] * 3)
    # Original battlespell[party_slot][spell_slot].
    battlespell: list[list[int | str]] = field(default_factory=lambda: [[0] * 18 for _ in range(3)])
    battlespellname: list[list[str]] = field(default_factory=lambda: [[" "] * 18 for _ in range(3)])
    battlespelldesc: list[list[str]] = field(default_factory=lambda: [[" "] * 18 for _ in range(3)])
    battlespellcost: list[list[float]] = field(default_factory=lambda: [[0.0] * 18 for _ in range(3)])
    battlespelltarget: list[list[int]] = field(default_factory=lambda: [[2] * 18 for _ in range(3)])
    battlespellspecial: list[list[int]] = field(default_factory=lambda: [[0] * 18 for _ in range(3)])
    queued: list[QueuedAction | None] = field(default_factory=lambda: [None] * 3)
    phase: str = "command"  # command | awaiting_resolution | enemy_turn | awaiting_wincombat | victory | done
    pending_option: CombatOption | None = None
    pending_item_slot: int | None = None
    pending_action_kind: str | None = None
    timer_alarm2: int | None = None
    feedback: str = ""
    spell_messages: list[str] = field(default_factory=list)
    pending_spell_effects: list[str] = field(default_factory=list)
    spell_message_history: list[tuple[int, int, tuple[str, ...]]] = field(default_factory=list)
    gold: int = 0
    xp: int = 0
    reward_gold: int = 0
    reward_exp: int = 0
    # A token, not an audio handle. AudioManager owns the actual playback.
    battle_music: str | None = None
    battle_music_volume: float = 0.7
    pending_ambush: int = 0  # scr_ambush is not supplied (ambush == 1)
    moveswapped: int = 0
    # scr_endturn selects an execution routine; it does not calculate its effects.
    resolution_stage: str | None = None
    pending_chained_encounter: int | None = None
    pending_turn_heals: list[tuple[int, int]] = field(default_factory=list)
    fightphase: int = 0
    # Screen coordinates in GML's 640x480 stage for obj_attackpress.
    attack_press_position: tuple[float, float] | None = None
    spell_phase_position: tuple[float, float] | None = None
    # Original obj_monsterparent stores these shared ACT order fields.
    simul_orders: dict[int, int] = field(default_factory=dict)
    simul_total: int = 0
    hero_attack_events: list[HeroHit] = field(default_factory=list)
    hero_spell_events: list[tuple[int, int | str]] = field(default_factory=list)
    spell_effect_outcomes: list[SpellOutcome] = field(default_factory=list)
    # scr_damage_enemy: obj_dmgwriter positions and hit info.
    damage_writer_events: list[DamageWriterEvent] = field(default_factory=list)
    # Animated spell object creation events, including delayed projectiles.
    spell_animation_events: list[SpellAnimationRequest] = field(default_factory=list)


class BattleCombatController:
    """The real controller starts at obj_encounterbasic's frame-24 handoff."""

    def __init__(self, layout, party_ids: Sequence[int], flags: MutableMapping[int, int], *,
                 chapter: int = 6, max_tension: float = 100.0,
                 inventory: Sequence[int] = (),
                 party_stats: Mapping[int, Mapping[str, int]] | None = None,
                 on_actions_ready: Callable[[list[QueuedAction]], None] | None = None,
                 on_victory_finished: Callable[[CombatState], None] | None = None,
                 ambush: int = 0, music: str | None = None,
                 equipped_weapons: Mapping[int, int] | None = None,
                 active_stream_song: str | None = None,
                 gold: int = 0, xp: int = 0,
                 monster_hooks: Mapping[str, MonsterHooks] | None = None,
                 party_auto: Mapping[int, int] | None = None,
                 on_wincombat: Callable[[CombatState], None] | None = None,
                 on_endturn: Callable[[CombatState], None] | None = None,
                 on_heal: Callable[[CombatActor, int], int | None] | None = None,
                 on_cursor_memory_reset: Callable[[CombatState], None] | None = None,
                 equipped_armors: Mapping[int, Sequence[int]] | None = None,
                 on_attack_phase: Callable[[CombatState], None] | None = None,
                 on_next_act: Callable[[CombatState], None] | None = None,
                 on_act_simul: Callable[[CombatState], None] | None = None,
                 on_chained_encounter: Callable[[CombatState, object], None] | None = None,
                 on_turn_committed: Callable[[CombatState], None] | None = None,
                 on_attack_press_start: Callable[[CombatState], None] | None = None,
                 on_spell_phase_start: Callable[[CombatState], None] | None = None,
                 on_act_started: Callable[[CombatState, CombatEnemy, int], None] | None = None,
                 on_bolt_check: Callable[[AttackPressPhase, int | None], None] | None = None,
                 on_hero_attack: Callable[[CombatState, CombatActor, int], None] | None = None,
                 on_spell_cast: Callable[[CombatState, int, str], bool | None] | None = None,
                 on_attack_press_finished: Callable[[CombatState], None] | None = None,
                 on_spell_retarget: Callable[[CombatState, int], None] | None = None,
                 on_spell_text_id: Callable[[int, CombatState, int], object] | None = None,
                 on_spell_item_shift: Callable[[int, int], None] | None = None,
                 on_spell_mercy_add: Callable[[CombatEnemy, int], None] | None = None,
                 on_spell_effect: Callable[[CombatState, CombatActor, int | str], None] | None = None,
                 on_hero_retarget: Callable[[CombatState, CombatActor, int], int | None] | None = None,
                 on_hero_damage: Callable[[CombatState, CombatActor, CombatEnemy, HeroHit], None] | None = None,
                 on_hero_sound: Callable[[str, float, CombatActor], None] | None = None,
                 sprite_frame_counts: Mapping[str, int] | None = None,
                 on_spell_animation: Callable[[CombatState, SpellAnimationRequest], None] | None = None,
                 on_spell_heal_modifier: Callable[[float, CombatState, int], float] | None = None,
                 spell_rng: Random | None = None):
        if len(party_ids) > 3 or not party_ids or party_ids[0] != 1:
            raise ValueError("Combat requires Kris first, with up to three party members")
        self.flags = flags
        self.layout = layout
        self.monster_hooks = dict(monster_hooks or {})
        self.party_auto = dict(party_auto or {})
        self.on_wincombat = on_wincombat
        self.on_endturn = on_endturn
        self.on_heal = on_heal
        self.on_cursor_memory_reset = on_cursor_memory_reset
        self.equipped_armors = {int(cid): tuple(items) for cid, items in (equipped_armors or {}).items()}
        self.on_attack_phase = on_attack_phase
        self.on_next_act = on_next_act
        self.on_act_simul = on_act_simul
        self.on_chained_encounter = on_chained_encounter
        self.on_turn_committed = on_turn_committed
        self.on_attack_press_start = on_attack_press_start
        self.on_spell_phase_start = on_spell_phase_start
        self.on_act_started = on_act_started
        self.on_bolt_check = on_bolt_check
        self.on_hero_attack = on_hero_attack
        self.on_spell_effect = on_spell_effect
        self.on_spell_animation = on_spell_animation
        self.on_spell_heal_modifier = on_spell_heal_modifier
        self.spell_rng = spell_rng or Random()
        self.on_hero_retarget = on_hero_retarget
        self.on_hero_damage = on_hero_damage
        self.on_hero_sound = on_hero_sound
        self.on_spell_cast = on_spell_cast
        self.on_spell_retarget = on_spell_retarget
        self.on_spell_text_id = on_spell_text_id
        self.on_spell_item_shift = on_spell_item_shift
        self.on_spell_mercy_add = on_spell_mercy_add
        self.on_attack_press_finished = on_attack_press_finished
        self.attack_press: AttackPressPhase | None = None
        self.spell_phase: SpellPhase | None = None
        self.rudebuster_animations: list[RudeBusterAnimation] = []
        self.rudebuster_bolts: list[RudeBusterBolt] = []
        self._victory_weapons = dict(equipped_weapons or {})
        self.on_actions_ready = on_actions_ready
        self.on_victory_finished = on_victory_finished
        self.spells: dict[int, list[CombatOption]] = {}
        self.acts: dict[tuple[int, int], list[CombatOption]] = {}
        self.items: dict[int, CombatOption] = {}
        self._inventory = list(inventory[:13]) + [0] * (13 - len(inventory[:13]))
        ids = tuple(list(party_ids) + [0] * (3 - len(party_ids)))
        stats = party_stats or {}
        actors = []
        for slot, char_id in enumerate(ids):
            if not char_id:
                continue
            entry = stats.get(char_id, {})
            x, y = layout.hero_positions[slot]
            actors.append(CombatActor(
                slot, char_id, x, y, CHAR_NAMES.get(char_id, f"Character {char_id}"),
                attack=entry.get("attack"), defense=entry.get("defense"),
                magic=entry.get("magic"), hp=entry.get("hp"),
                max_hp=entry.get("max_hp"),
            ))
        enemies = [CombatEnemy(i, e.object_name, e.monster_type, e.x, e.y,
                               e.object_name.removeprefix("obj_").removesuffix("_enemy").replace("_", " ").title())
                   for i, e in enumerate(layout.enemy_definitions)]
        self.state = CombatState(layout.number, chapter, ids, layout.battle_message, actors, enemies,
                                 maxtension=max_tension, battle_music=music,
                                 gold=gold, xp=xp)
        for actor in actors:
            actor.hero_animation = HeroCombatAnimation(actor, hero_profile(
                actor.character_id, chapter=chapter, encounter_no=layout.number,
                weapon=self._victory_weapons.get(actor.character_id),
                flag_1311=bool(flags.get(1311, 0)),
                sprite_frame_counts=sprite_frame_counts,
            ))
        s = self.state
        # obj_battlecontroller Create initializes flags and party arrays.
        if s.encounter_no == 73:
            s.fc, s.fe = 3, 4
            flags[62] = 1
        if flags.get(62, 0) == 0:
            s.fc = s.fe = 0
            s.typer = s.battletyper = 4
        flags[62] = 0
        for k in (50, 51, 52, 53, 63, 36, 39):
            flags[k] = 0
        for slot, actor_id in enumerate(ids):
            if actor_id:
                s.charmove[slot] = s.charcantarget[slot] = 1
                s.chardead[slot] = 0
                s.havechar[actor_id - 1] = 1
                s.charpos[actor_id - 1] = slot
                s.chartotal += 1
                actor = next(a for a in actors if a.slot == slot)
                # GML: if (i == 2 && global.charweapon[3] == 35)
                #     _at=12; _df=3; _mag=3;
                bonus = (12, 3, 3) if slot == 2 and (equipped_weapons or {}).get(3) == 35 else (0, 0, 0)
                s.battleat[slot] = actor.attack + bonus[0] if actor.attack is not None else None
                s.battledf[slot] = actor.defense + bonus[1] if actor.defense is not None else None
                s.battlemag[slot] = actor.magic + bonus[2] if actor.magic is not None else None
        # Source Create: reset every monster stat/ACT slot *before* spawning
        # occupied instances, and call User[12] then User[15] for each.
        for monster_slot in s.monster_slots:
            enemy = next((e for e in s.enemies if e.slot == monster_slot.index), None)
            hooks = (self.monster_hooks.get(enemy.object_name, self.monster_hooks.get("*"))
                     if enemy else self.monster_hooks.get("*"))
            scr_monster_statreset(monster_slot, hooks)
        for enemy in s.enemies:
            scr_monster_makeinstance(
                s.monster_slots[enemy.slot], enemy,
                self.monster_hooks.get(enemy.object_name, self.monster_hooks.get("*")),
            )
        for slot in range(3):
            s.temptension[slot] = 0
            for item_idx, value in enumerate(self._inventory):
                s.tempitem[item_idx][slot] = value
        if active_stream_song and music and active_stream_song == music and active_stream_song != "battle.ogg":
            s.battle_music_volume = 1.0
        if ambush == 1:
            # scr_ambush is an external routine and must be provided later.
            s.pending_ambush = 1
        if ambush == 2:
            for enemy in s.enemies:
                enemy.first_strike = True
            # GML round() is nearest integer for nonnegative TP.
            s.tension = floor(max_tension / 4 + 0.5)
        self._finished_callback_called = False

    def set_enemy_stats(self, slot: int, *, name: str | None = None,
                        hp: int | None = None, max_hp: int | None = None,
                        mercy: float | None = None, mercy_max: float | None = None,
                        attack: int | None = None, defense: int | None = None,
                        gold: int | None = None, exp: int | None = None,
                        spare_point: int | None = None, hit_target: int | None = None,
                        comment: str | None = None, attack_name: str | None = None,
                        status: int | None = None, tired: bool | None = None,
                        cant_spare: bool | None = None, active: bool | None = None):
        """Update known fields (normally assigned in monster User[12]/User[15])."""
        enemy = next((e for e in self.state.enemies if e.slot == slot), None)
        if enemy is None:
            raise IndexError(f"No instantiated enemy in monster slot {slot}")
        changed_stats = False
        for field_name, value in locals().copy().items():
            if field_name in {
                "name", "hp", "max_hp", "mercy", "mercy_max", "attack",
                "defense", "gold", "exp", "spare_point", "hit_target",
                "comment", "attack_name", "status", "tired", "cant_spare", "active"
            } and value is not None:
                setattr(enemy, field_name, value)
                if field_name != "active":
                    changed_stats = True
        if tired is not None:
            enemy.status = int(tired)
        elif status is not None:
            enemy.tired = status == 1
        if changed_stats:
            enemy.stats_loaded = True
        self.state.monster_slots[slot].sync_from_enemy(enemy)

    def register_spells(self, party_slot: int, options: Sequence[CombatOption]):
        if not 0 <= party_slot < 3:
            raise IndexError(party_slot)
        if len(options) > 18:
            raise ValueError("The source allocates 18 battle spell slots")
        self.spells[party_slot] = list(options)
        s = self.state
        for idx, option in enumerate(options):
            s.battlespell[party_slot][idx] = option.code
            s.battlespellname[party_slot][idx] = option.name
            s.battlespelldesc[party_slot][idx] = option.description
            s.battlespellcost[party_slot][idx] = option.tp_cost
            s.battlespelltarget[party_slot][idx] = option.target

    def register_acts(self, enemy_slot: int, char_id: int, options: Sequence[CombatOption]):
        if len(options) > 6:
            raise ValueError("The source ACT menu has six slots")
        self.acts[(enemy_slot, char_id)] = list(options)

    def register_item(self, item_id: int, option: CombatOption):
        self.items[item_id] = option

    def replace_inventory(self, inventory: Sequence[int]):
        """Update global.item[] after a future item-consumption script runs.

        scr_mnendturn copies indices 0..11 of this authoritative inventory
        into every party member's temporary menu snapshot.
        """
        values = list(inventory[:13])
        self._inventory = values + [0] * (13 - len(values))

    def _actor(self):
        return next((a for a in self.state.actors if a.slot == self.state.charturn), None)

    def _options(self):
        s = self.state
        if s.bmenuno == 2:
            return self.spells.get(s.charturn, [])
        if s.bmenuno == 4:
            return [(i, self.items.get(s.tempitem[i][s.charturn]))
                    for i in range(13) if s.tempitem[i][s.charturn] != 0]
        if s.bmenuno == 9:
            actor = self._actor()
            return self.acts.get((s.bmenucoord[11][s.charturn], actor.character_id), []) if actor else []
        return []

    def _option_entries(self):
        """Return original slot indices and options, respecting holes."""
        s = self.state
        if s.bmenuno == 2:
            return list(enumerate(self.spells.get(s.charturn, [])))
        if s.bmenuno == 4:
            return [(idx, self.items.get(s.tempitem[idx][s.charturn]))
                    for idx in range(13) if s.tempitem[idx][s.charturn] and
                    s.tempitem[idx][s.charturn] in self.items]
        if s.bmenuno == 9:
            actor = self._actor()
            return list(enumerate(self.acts.get((s.bmenucoord[11][s.charturn], actor.character_id), []))) if actor else []
        return []

    def _target_entries(self):
        s = self.state
        if s.bmenuno in TARGET_ENEMY_MENUS:
            return [e.slot for e in s.enemies if e.active]
        return [a.slot for a in s.actors if a.can_target]

    def _move_on_grid(self, key: str):
        s = self.state
        entries = [i for i, _ in self._option_entries()]
        if not entries:
            return
        n = s.bmenuno
        old = s.bmenucoord[n][s.charturn]
        if old not in entries:
            old = entries[0]
        if key == "Left":
            choice = old - 1 if old % 2 else old + 1
        elif key == "Right":
            choice = old + 1 if old % 2 == 0 else old - 1
        elif key == "Up":
            choice = old - 2
        else:
            choice = old + 2
        if choice in entries:
            s.bmenucoord[n][s.charturn] = choice

    def _target_move(self, key: str):
        s = self.state
        entries = self._target_entries()
        if not entries:
            return
        current = s.bmenucoord[s.bmenuno][s.charturn]
        index = entries.index(current) if current in entries else 0
        direction = 1 if key == "Down" else -1
        s.bmenucoord[s.bmenuno][s.charturn] = entries[(index + direction) % len(entries)]

    def _queue(self, kind: str, target: int | None = None, option: CombatOption | None = None,
               item_slot: int | None = None):
        s = self.state
        slot = s.charturn
        s.temptension[slot] = s.tension
        s.queued[slot] = QueuedAction(slot, kind, target, option, item_slot)
        codes = {"fight": (1, 1), "spare": (2, 10), "defend": (10, 4)}
        if kind in codes:
            s.charaction[slot], s.faceaction[slot] = codes[kind]
        s.chartarget[slot] = target if target is not None else 0
        if kind == "spare":
            s.charspecial[slot] = 100
        if kind == "defend":
            s.tension = min(s.maxtension, s.tension + 40)
        if kind in {"spell", "act"} and option is not None:
            s.tension -= option.tp_cost
        if kind == "act":
            # scr_actselect hasn't been supplied yet, but this much is known:
            # scr_endturn starts with acting[0] for Kris, or actingsingle[]
            # for another party member. Preserve the ACT target and choice.
            s.actingsingle[slot] = 1
            s.actingtarget[slot] = target if target is not None else 0
            s.actingsimul[slot] = int(bool(option and option.simultaneous))
            if s.party_ids[slot] == 1:
                s.acting_flags[0] = 1
        s.pending_option = None
        s.pending_item_slot = None
        s.pending_action_kind = None
        s.tensionselect = 0
        s.bmenuno = 0
        next_slots = [a.slot for a in s.actors if a.slot > slot and a.can_move and not a.dead and not self.party_auto.get(a.character_id, 0)]
        if next_slots:
            s.charturn = next_slots[0]
        else:
            s.phase = "awaiting_resolution"
            s.feedback = "Actions queued; awaiting attack/ACT resolution."
            if self.on_actions_ready is not None:
                self.on_actions_ready([a for a in s.queued if a is not None])
            # scr_nexthero calls scr_endturn when the last character commits.
            # The attack-phase or ACT callbacks run *after* the inventory commit.
            self.end_turn()

    def _open_command(self):
        s = self.state
        choice = s.bmenucoord[0][s.charturn]
        if choice == 0:
            s.bmenuno = 1
        elif choice == 1:
            s.bmenuno = 11 if s.party_ids[s.charturn] == 1 else 2
        elif choice == 2:
            if any(s.tempitem[i][s.charturn] in self.items for i in range(13)
                   if s.tempitem[i][s.charturn]):
                s.bmenuno = 4
            else:
                s.feedback = "No battle item definitions have been loaded."
        elif choice == 3:
            s.bmenuno = 12
        else:
            self._queue("defend")

    def _select_target(self):
        s = self.state
        if not self._target_entries():
            s.feedback = "No valid targets."
            return
        enemy_slot = s.bmenucoord[s.bmenuno][s.charturn]
        if enemy_slot not in self._target_entries():
            enemy_slot = self._target_entries()[0]
        n = s.bmenuno
        if n == 1:
            self._queue("fight", enemy_slot)
        elif n == 12:
            self._queue("spare", enemy_slot)
        elif n == 11:
            s.bmenucoord[11][s.charturn] = enemy_slot
            s.bmenuno = 9
            s.bmenucoord[9][s.charturn] = 0
        elif n in (3, 8, 13):
            self._queue(s.pending_action_kind or "spell", enemy_slot, s.pending_option)
        elif n == 7:
            self._queue("item", enemy_slot, s.pending_option, s.pending_item_slot)

    def _select_option(self):
        s = self.state
        entries = dict(self._option_entries())
        idx = s.bmenucoord[s.bmenuno][s.charturn]
        option = entries.get(idx)
        if option is None:
            s.feedback = "That action has no loaded definition."
            return
        if option.tp_cost > s.tension:
            s.feedback = "Not enough TP."
            return
        if any(s.havechar[cid - 1] == 0 for cid in option.required_character_ids):
            s.feedback = "A required party member is missing."
            return
        if s.bmenuno == 9:
            # scr_actselect uses the target already chosen by menu 11;
            # ACT is queued here, not followed by another target menu.
            s.acting_choice[s.charturn] = idx
            self._queue("act", target=s.bmenucoord[11][s.charturn], option=option)
            return
        elif s.bmenuno == 4:
            s.pending_action_kind = "item"
            s.pending_item_slot = idx
        else:
            s.pending_action_kind = "spell"
        s.pending_option = option
        if option.target == 0 or (s.pending_action_kind == "item" and option.target == 2):
            self._queue(s.pending_action_kind, option=option, item_slot=s.pending_item_slot)
        else:
            s.bmenuno = ({1: 8, 2: 3, 3: 13}.get(option.target, 3)
                         if s.pending_action_kind == "spell"
                         else (7 if option.target == 1 else 13))
            s.bmenucoord[s.bmenuno][s.charturn] = 0

    def _back(self):
        s = self.state
        n = s.bmenuno
        if n == 0:
            previous = [a.slot for a in s.actors if a.slot < s.charturn and s.queued[a.slot] is not None]
            if previous:
                s.charturn = previous[-1]
                s.queued[s.charturn] = None
                s.charaction[s.charturn] = s.faceaction[s.charturn] = 0
                s.charspecial[s.charturn] = 0
                s.chartarget[s.charturn] = 0
                s.acting_flags[s.charturn] = 0
                s.actingsingle[s.charturn] = 0
                s.actingsimul[s.charturn] = 0
                s.actingtarget[s.charturn] = 0
                # Cancel a prior Defend/TP change by restoring snapshot.
                s.tension = s.temptension[s.charturn]
                s.bmenuno = s.rembmenuno[s.charturn]
        elif n == 9:
            s.bmenuno = 11
        elif n in (1, 11, 12, 2, 4):
            s.bmenuno = 0
        elif n == 7:
            s.bmenuno = 4
        elif n in (3, 8, 13):
            s.bmenuno = 2 if s.pending_action_kind == "spell" else 9 if s.pending_action_kind == "act" else 4
            s.pending_option = None
            s.tensionselect = 0

    def handle_key(self, key: str):
        """One KeyPress event; game.py debounces held keys."""
        s = self.state
        if s.phase == "victory":
            if key.lower() in ("z", "return", "space", "x"):
                s.victory_message_dismissed = True
            return
        # obj_rudebuster_bolt reads the same button1_p input even when the
        # parent spell-phase (or the command UI) has otherwise advanced.
        if key.lower() in ("z", "return", "space"):
            for bolt in self.rudebuster_bolts:
                bolt.button(key)
        if s.phase == "awaiting_resolution" and s.resolution_stage == "attack_press":
            if self.attack_press is not None:
                self.attack_press.button(key)
            return
        if s.phase != "command":
            return
        if key in ("Left", "Right", "Up", "Down"):
            if s.bmenuno == 0 and key in ("Left", "Right"):
                v = s.bmenucoord[0][s.charturn]
                s.bmenucoord[0][s.charturn] = (v + (-1 if key == "Left" else 1)) % 5
            elif s.bmenuno in PAGE_MENUS:
                self._move_on_grid(key)
            elif s.bmenuno in TARGET_MENUS and key in ("Up", "Down"):
                self._target_move(key)
            s.feedback = ""
        elif key.lower() in ("x", "backspace"):
            self._back()
        elif key.lower() in ("z", "return", "space"):
            if s.bmenuno == 0:
                self._open_command()
            elif s.bmenuno in TARGET_MENUS:
                self._select_target()
            elif s.bmenuno in PAGE_MENUS:
                self._select_option()

    def deactivate_enemy(self, slot: int):
        """Mark a defeated/spared monster absent; effects come from other scripts."""
        enemy = next((e for e in self.state.enemies if e.slot == slot), None)
        if enemy is None:
            raise IndexError(f"No monster in slot {slot}")
        enemy.active = False
        self.state.monster_slots[slot].sync_from_enemy(enemy)

    def defeat_enemy(self, slot: int, *, outcome: int | None = None,
                     call_user10: bool = False) -> bool:
        """Source scr_monsterdefeat: single collection point for rewards/flags."""
        enemy = next((e for e in self.state.enemies if e.slot == slot), None)
        if enemy is None or not enemy.active:
            return False
        if outcome is not None:
            self.flags[51 + slot] = int(outcome)
        hooks = self.monster_hooks.get(enemy.object_name, self.monster_hooks.get("*"))
        return scr_monsterdefeat(enemy, self.state, self.flags, hooks,
                                call_user10=call_user10)

    def damage_enemy(self, slot: int, amount: int, caster_slot: int) -> int | None:
        """Source scr_damage_enemy(arg0, arg1), including its event order.

        The external GML `caster` variable is supplied as caster_slot. It
        controls the damage-writer portrait, not the amount of damage.
        Unknown HP is never replaced with a fictional zero. Unlike the prior
        stand-in, this routine does not clamp negative supplied damage.
        """
        s = self.state
        enemy = next((e for e in s.enemies if e.slot == slot and e.active), None)
        if enemy is None or enemy.hp is None:
            return None
        amount = int(amount)
        # GML creates the writer before subtracting HP; its y coordinate
        # stacks upward by 20 pixels for previous hits on the same monster.
        type_id = None
        if 0 <= caster_slot < 3 and s.party_ids[caster_slot] != 0:
            char_id = s.party_ids[caster_slot]
            type_id = 6 if char_id == 4 else char_id - 1
        elif caster_slot == 5:
            type_id = 5
        writer = DamageWriterEvent(slot, enemy.x,
                                   enemy.y + 20 - s.hittarget[slot] * 20,
                                   amount, type=type_id)
        s.damage_writer_events.append(writer)
        enemy.hp -= amount
        actor = next((a for a in s.actors if a.slot == caster_slot), None)
        hooks = self.monster_hooks.get(enemy.object_name, self.monster_hooks.get('*'))
        if hooks is not None and hooks.on_damage is not None:
            # GameMaker callback_on_damage(id) is invoked after HP decreases.
            hooks.on_damage(enemy, actor, amount)
        if amount > 0:
            enemy.shakex = 9
            enemy.state = 3
            enemy.hurttimer = 30
            enemy.hurtamt = amount
        s.hittarget[slot] += 1
        enemy.hit_target += 1
        if amount == 0:
            enemy.hurtamt = 0
            if enemy.hurttimer <= 15 and enemy.candodge == 1:
                enemy.dodgetimer = 0
                enemy.state = 4
        # GML checks lethal HP only AFTER callback and hit reaction.
        if enemy.hp <= 0 and enemy.active:
            self.defeat_enemy(slot)
        else:
            s.monster_slots[slot].sync_from_enemy(enemy)
        return amount

    scr_damage_enemy = damage_enemy

    def _notify_battle_sound(self, sound_name: str, pitch: float) -> None:
        """Animation-object audio event; no sound or pitch is fabricated."""
        callback = self.on_hero_sound
        if callback is not None:
            actor = next((a for a in self.state.actors if a.character_id == 2), None)
            if actor is not None:
                callback(sound_name, pitch, actor)

    def _emit_spell_animation(self, request: SpellAnimationRequest) -> None:
        """Instantiate ported effects, forward all others as object requests."""
        self.state.spell_animation_events.append(request)
        if request.object_name == 'obj_rudebuster_anim':
            self.rudebuster_animations.append(RudeBusterAnimation.from_request(self, request))
        elif request.object_name == 'obj_rudebuster_bolt':
            self.rudebuster_bolts.append(RudeBusterBolt.from_request(self, request))
        if self.on_spell_animation is not None:
            self.on_spell_animation(self.state, request)

    scr_monsterdefeat = defeat_enemy

    def spell_effect(self, code: int, caster_slot: int) -> SpellOutcome:
        """Direct GML-compatible entry for scr_spell(arg0, arg1)."""
        return scr_spell(self, code, caster_slot)

    scr_spell = spell_effect

    def _heal_character(self, actor: CombatActor, amount: int) -> None:
        """Invoke the eventual scr_heal adapter, or apply the basic HP amount."""
        if self.on_heal is not None:
            self.on_heal(actor, amount)
        elif actor.hp is not None and actor.max_hp is not None:
            actor.hp = min(actor.max_hp, actor.hp + amount)
        actor.dead = actor.hp is not None and actor.hp <= 0
        self.state.chardead[actor.slot] = int(actor.dead)

    def end_turn(self):
        """Port scr_endturn: commit inventory and dispatch the action phase.

        Dispatches the recovered phase-selection and ACT-order routines,
        but does not execute queued damage, items, spells, or enemy AI.
        """
        s = self.state
        if s.phase in ("victory", "done", "awaiting_wincombat", "enemy_turn", "chained_encounter"):
            return

        if s.resolution_stage is not None and s.phase == "awaiting_resolution":
            return  # A second endturn call must not commit/evaluate twice.

        # The source copies the currently selected tempitem column into
        # global.item[0..11]; slot 12 is intentionally untouched.
        if not 0 <= s.charturn < 3:
            # The AUTO-party path may arrive here with charturn == 3. In that
            # situation, no valid GML tempitem column exists: keep inventory.
            source_slot = None
        else:
            source_slot = s.charturn
        if source_slot is not None:
            for index in range(12):
                self._inventory[index] = s.tempitem[index][source_slot]
        for index in range(12):
            for slot in range(3):
                s.tempitem[index][slot] = self._inventory[index]
        s.moveswapped = 0
        s.attacking = 0
        s.pending_turn_heals.clear()

        # Source checks party positions 0/1/2 against armor[1]/[2]/[3].
        # It does NOT index armor by the potentially reordered party char ID.
        for slot in range(3):
            actor = next((a for a in s.actors if a.slot == slot), None)
            equipped = self.equipped_armors.get(slot + 1, ())
            if actor is not None and s.faceaction[slot] == 4 and 38 in equipped:
                if actor.max_hp is not None:
                    heal = floor(actor.max_hp * 0.16 + 0.5)
                    self._heal_character(actor, heal)
                    s.pending_turn_heals.append((slot, heal))
                    actor.tu += 1
            # Nested original loop subtracts 3 from tu *per* party slot.
            if actor is not None:
                actor.tu -= 3

        for slot, cid in enumerate(s.party_ids):
            s.monsterattackname[slot] = " "
            if cid and self.party_auto.get(cid, 0) and any(e.active for e in s.enemies):
                # The last assignment in GML's 2, 1, 0 test wins, so the
                # lowest active monster slot takes priority.
                s.chartarget[slot] = min(e.slot for e in s.enemies if e.active)
            if s.charaction[slot] == 1:
                s.attacking = 1

        s.messagepriority = s.attackpriority = -1
        s.phase = "awaiting_resolution"
        if self.on_turn_committed is not None:
            self.on_turn_committed(s)

        if s.acting_flags[0] == 1 or any(v == 1 for v in s.actingsingle):
            s.charturn = 3
            s.myfight = 3
            s.currentactingchar = 0
            if s.acting_flags[0] == 1 and s.actingsimul[0] == 1:
                self.act_simul()
            elif s.acting_flags[0] == 0:
                self.next_act()
            else:
                # The first (Kris) ACT is driven by its enemy event. Later,
                # that event calls next_act() when its effect is finished.
                s.resolution_stage = "act"
                s.feedback = "Kris ACT awaits its monster event."
                enemy = self._active_enemy_for_act(0)
                if enemy is not None:
                    enemy.actcon = 1
                    enemy.acting = 1
                    if self.on_act_started is not None:
                        self.on_act_started(s, enemy, 0)
        else:
            self.attack_phase()
        if self.on_endturn is not None:
            self.on_endturn(s)

    def _active_enemy_for_act(self, party_slot: int) -> CombatEnemy | None:
        """Resolve global.monsterinstance[global.actingtarget[slot]]."""
        if not 0 <= party_slot < 3:
            return None
        target = self.state.actingtarget[party_slot]
        return next((e for e in self.state.enemies
                     if e.slot == target and e.active), None)

    def _notify_act_started(self, slot: int, enemy: CombatEnemy) -> None:
        if self.on_act_started is not None:
            self.on_act_started(self.state, enemy, slot)

    def attack_phase(self) -> None:
        """scr_attackphase: choose obj_attackpress versus obj_spellphase.

        Merely entering either phase does not simulate the object Step events.
        In GML, myfight==4 overrides the spell/action phase and forces the
        attack-press phase. Use the pre-transition value for that check.
        """
        s = self.state
        if s.phase in ("victory", "done", "chained_encounter"):
            return
        if monster_population(s.enemies) == 0:
            self.win_combat()
            return
        s.hittarget[:] = [0, 0, 0]
        for slot in s.monster_slots:
            slot.hittarget = 0
        for enemy in s.enemies:
            enemy.hit_target = 0
        prior_myfight = s.myfight
        # scr_itemconsumeb, scr_spellconsumeb, and scr_actselect haven't
        # been recovered to supply their exact charaction[] codes. Until
        # then, recognize their registered queued kinds as spell-phase work
        # *without* fabricating numeric action codes or their effects.
        uses_spell_phase = (any(action in (2, 4) for action in s.charaction)
                            or any(q is not None and q.kind in ("act", "spell", "item")
                                   for q in s.queued))
        s.fightphase = 0 if uses_spell_phase else 1
        if prior_myfight == 4:
            s.fightphase = 1
        s.charturn = 3
        s.phase = "awaiting_resolution"
        s.attack_press_position = None
        s.spell_phase_position = None
        if s.fightphase == 1:
            s.myfight = 1
            camera_x, camera_y = self.layout.camera_origin
            s.attack_press_position = (camera_x + 2, camera_y + 365)
            s.resolution_stage = "attack_press"
            self.spell_phase = None
            self.attack_press = AttackPressPhase(
                s, self.flags, self.party_auto,
                equipped_weapons=self._victory_weapons,
                on_bolt_check=self.on_bolt_check,
                on_attack_trigger=self._hero_attack_started,
                on_finish=self._finish_attack_press,
            )
            s.feedback = "Time your attack (Z; X/C for 3-button mode)."
            if self.on_attack_press_start is not None:
                self.on_attack_press_start(s)
        else:
            s.myfight = 4
            s.spell_phase_position = (0, 0)
            s.resolution_stage = "spell_phase"
            self.attack_press = None
            self.spell_phase = SpellPhase(
                s, on_cast=self._handle_spell_cast,
                on_finish=self._finish_spell_phase,
            )
            s.feedback = "Resolving spells and items in party order."
            if self.on_spell_phase_start is not None:
                self.on_spell_phase_start(s)
        if self.on_attack_phase is not None:
            self.on_attack_phase(s)

    def spell_text(self, code: int, caster_slot: int):
        """Run the recovered scr_spelltext, return its source message result."""
        result = scr_spelltext(
            code, caster_slot, self.state,
            on_retarget=self.on_spell_retarget,
            on_text_id=self.on_spell_text_id,
            on_item_shift=self.on_spell_item_shift,
            on_mercy_add=self.on_spell_mercy_add,
        )
        self.state.spell_messages = list(result.messages)
        self.state.pending_spell_effects = list(result.pending_effects)
        if result.messages:
            self.state.spell_message_history.append((caster_slot, code, result.messages))
        return result

    def _handle_spell_cast(self, state: CombatState, slot: int, kind: str) -> bool:
        """SpellPhase cast entry: announce original script message, then writer hook.

        Actual item/spell effects and the battle text writer are still owned
        by external object scripts; returning True means a writer is alive.
        """
        queued = state.queued[slot]
        spell_code = (state.charspecial[slot] if state.charspecial[slot] else
                      queued.option.code if queued is not None and queued.option is not None
                      else 0)
        if isinstance(spell_code, int):
            self.spell_text(spell_code, slot)
        if self.on_spell_cast is not None:
            return bool(self.on_spell_cast(state, slot, kind))
        return False

    def _hero_attack_started(self, state: CombatState, actor: CombatActor, slot: int) -> None:
        """obj_attackpress User[1] sets the hero attack animation, not damage."""
        if self.on_hero_attack is not None:
            self.on_hero_attack(state, actor, slot)

    def _resolve_hero_attack(self, actor: CombatActor) -> HeroHit:
        """obj_heroparent Step delayed hit; scr_monsterdefeat is integrated.

        Retargeting still needs an external script; no invented dead-target swap.
        """
        s = self.state
        target_slot = s.chartarget[actor.slot]
        if self.on_hero_retarget is not None:
            redirected = self.on_hero_retarget(s, actor, target_slot)
            if redirected is not None:
                target_slot = int(redirected)
                s.chartarget[actor.slot] = target_slot
        enemy = next((e for e in s.enemies if e.slot == target_slot and e.active), None)
        if enemy is None:
            result = HeroHit(actor.slot, target_slot, actor.points, None, None, False, False)
        else:
            # obj_heroparent: Susie's attack with any equipped weapon 54
            # invokes scr_healitemspell(ceil(maxhp[2] * 0.1)) before damage.
            # scr_healitemspell itself is still unavailable, so on_heal can
            # override the existing basic HP fallback as in other healing.
            if (actor.character_id == 2 and 54 in self._victory_weapons.values()
                    and actor.max_hp is not None):
                self._heal_character(actor, ceil(actor.max_hp * .1))
            trashy = any(e.active and e.object_name == 'obj_trashy_trio' for e in s.enemies)
            damage = calculate_attack_damage(
                s.battleat[actor.slot], actor.points, enemy.defense, enemy.monster_type,
                trashy_trio_present=trashy)
            # HP and defense come from monster User[12]/User[15]. A name or
            # monster type alone does not make either value available.
            valid = damage is not None and enemy.hp is not None
            if valid:
                if not trashy:
                    enemy.hp -= damage
                s.hittarget[target_slot] += 1
                enemy.hit_target += 1
                defeated = enemy.hp <= 0 and not trashy
                if damage > 0:
                    # scr_tensionheal is not supplied; default raw TP gain is
                    # original round(points / 10), with type-20 bonus divisor.
                    gain = gml_round(actor.points / (15 if s.enemies and s.enemies[0].monster_type == 20 else 10))
                    s.tension = min(s.maxtension, s.tension + gain)
                s.monster_slots[target_slot].sync_from_enemy(enemy)
            else:
                defeated = False
            result = HeroHit(actor.slot, target_slot, actor.points, damage,
                             enemy.hp, defeated, valid)
            if valid:
                hooks = self.monster_hooks.get(enemy.object_name, self.monster_hooks.get('*'))
                if hooks is not None and hooks.on_damage is not None:
                    hooks.on_damage(enemy, actor, damage)
                if self.on_hero_damage is not None:
                    self.on_hero_damage(s, actor, enemy, result)
                # The damage callback can change HP, so recheck before defeat.
                if not trashy and enemy.hp is not None and enemy.hp <= 0:
                    self.defeat_enemy(target_slot)
                    if actor.is_auto_susie:
                        self.flags[51 + target_slot] = 5
        s.hero_attack_events.append(result)
        return result

    def _resolve_hero_spell(self, actor: CombatActor) -> None:
        """obj_heroparent invokes scr_spell 16 ticks after casting starts.

        Spell narration runs earlier; animation-owned effects remain requests.
        """
        s = self.state
        slot = actor.slot
        queued = s.queued[slot]
        spell = (s.charspecial[slot] if s.charspecial[slot] else
                 queued.option.code if queued is not None and queued.option is not None
                 else 0)
        s.hero_spell_events.append((slot, spell))
        if isinstance(spell, int):
            self.spell_effect(spell, slot)
        if self.on_spell_effect is not None:
            # Backward-compatible observer/extension hook, *after* GML effect.
            self.on_spell_effect(s, actor, spell)

    def _finish_attack_press(self, phase: AttackPressPhase) -> None:
        """Draw[0] completion: win or hand control to the enemy turn scripts."""
        s = self.state
        if s.phase != "awaiting_resolution" or s.resolution_stage != "attack_press":
            return
        if monster_population(s.enemies) == 0:
            self.win_combat()
        else:
            if s.mnfight not in (1.5, 2):
                s.mnfight = 1
            s.myfight = -1
            s.resolution_stage = "enemy_turn_pending"
            s.feedback = "Enemy turn ready; waiting for monster attack script."
            if self.on_attack_press_finished is not None:
                self.on_attack_press_finished(s)

    def _finish_spell_phase(self, phase: SpellPhase) -> None:
        """obj_spellphase Step: scr_attackphase() after the final caster."""
        if self.state.phase != "awaiting_resolution" or self.spell_phase is not phase:
            return
        self.spell_phase = None
        self.attack_phase()  # myfight==4 forces the attackpress handoff.

    def dismiss_spell_text(self) -> None:
        """Signal that the battle writer created by scr_battletext_default ended."""
        if self.spell_phase is not None:
            self.spell_phase.dismiss_text()

    def next_act(self) -> None:
        """scr_nextact: finish an ACT and move to the next single ACT.

        Call again after the enemy object finishes the currently active ACT.
        Only ACT selection/order is implemented here; no ACT effect runs.
        """
        s = self.state
        if s.phase in ("victory", "done", "chained_encounter"):
            return
        s.acting_flags[:] = [0, 0, 0]
        current = s.currentactingchar
        if 0 <= current < 3:
            s.actingsingle[current] = 0
            previous_enemy = self._active_enemy_for_act(current)
            if previous_enemy is not None:
                for name in ("acting", "actcon", "actconsus", "actconral", "actconnoe"):
                    setattr(previous_enemy, name, 0)
        found_single = False
        for slot in range(max(0, current + 1), 3):
            s.currentactingchar = slot
            if s.actingsingle[slot] != 1:
                continue
            enemy = self._active_enemy_for_act(slot)
            if enemy is None:
                # The source assumes global.monsterinstance exists; until
                # monster defeat mechanics are ported, don't start a dead ACT.
                s.actingsingle[slot] = 0
                continue
            char_id = s.party_ids[slot]
            flag_name = {2: "actconsus", 3: "actconral", 4: "actconnoe"}.get(char_id)
            if flag_name is None:
                # Source only dispatches Susie, Ralsei, Noelle in this loop.
                continue
            setattr(enemy, flag_name, 1)
            enemy.acting = 1
            found_single = True
            s.resolution_stage = "next_act"
            s.feedback = f"{CHAR_NAMES[char_id]} ACT awaits its monster event."
            self._notify_act_started(slot, enemy)
            if s.actingsimul[slot]:
                self.act_simul()
            break
        if not found_single:
            # scr_nextact clears parent flags and continues to attackphase.
            s.currentactingchar = 0
            for enemy in s.enemies:
                if enemy.active:
                    for name in ("acting", "actingsus", "actingral", "actingnoe"):
                        setattr(enemy, name, 0)
            self.attack_phase()
        if self.on_next_act is not None:
            self.on_next_act(s)

    def act_simul(self) -> None:
        """scr_act_simul: register in-order simultaneous ACT participants.

        Only ACTs with an explicitly registered simultaneous=True option
        have global.actsimul[monster][choice]==1. Enemy scripts consume the
        actcon* flags and simultotal; the effects are intentionally external.
        """
        s = self.state
        if s.phase in ("victory", "done", "chained_encounter"):
            return
        orders: dict[int, int] = {}
        for slot in range(max(0, s.currentactingchar), 3):
            if s.actingsingle[slot] != 1:
                continue
            enemy = self._active_enemy_for_act(slot)
            if enemy is None:
                continue
            cid = s.party_ids[slot]
            choice = s.acting_choice[slot]
            registered = self.acts.get((enemy.slot, cid), [])
            if not (0 <= choice < len(registered) and registered[choice].simultaneous):
                continue
            orders[cid] = len(orders)
            field_name = {1: "simulorderkri", 2: "simulordersus", 3: "simulorderral", 4: "simulordernoe"}.get(cid)
            if field_name:
                # In original GML this field is stored on obj_monsterparent;
                # keep it visible on each monster plus in the shared state.
                for parent in s.enemies:
                    if parent.active:
                        setattr(parent, field_name, orders[cid])
            setattr(enemy, {1: "actcon", 2: "actconsus", 3: "actconral", 4: "actconnoe"}[cid],
                    0 if cid == 1 else 1)
            enemy.acting = 1
            s.actingsingle[slot] = 0
            self._notify_act_started(slot, enemy)
        s.simul_orders = orders
        s.simul_total = len(orders)
        for enemy in s.enemies:
            if enemy.active:
                enemy.simultotal = s.simul_total
        s.phase = "awaiting_resolution"
        s.resolution_stage = "act_simul"
        s.feedback = ("Simultaneous ACT awaits the monster event."
                      if orders else "No registered simultaneous ACTs to dispatch.")
        if self.on_act_simul is not None:
            self.on_act_simul(s)

    # GameMaker naming aliases for adapters working directly from GML names.
    scr_attackphase = attack_phase
    scr_nextact = next_act
    scr_act_simul = act_simul

    def inventory_snapshot(self) -> tuple[int, ...]:
        """Current Dark World global.item[]; never uses LW_inventory."""
        return tuple(self._inventory)

    def win_combat(self):
        """Port scr_wincombat, including the flag[60] chained-encounter path.

        Defeats all remaining live enemies through scr_monsterdefeat, including
        their reward totals, disposition counters, and completion flags.
        """
        s = self.state
        if s.victoried or s.phase in ("victory", "done", "chained_encounter"):
            return
        normal_victory = not self.flags.get(60, 0) or self.flags.get(36, 0) == 1
        # Both branches invoke the recovered monster defeat script first.
        for enemy in list(s.enemies):
            if enemy.active:
                self.defeat_enemy(enemy.slot)

        if normal_victory:
            s.myfight, s.mnfight = 7, -1
            s.victory = 1
            self.begin_victory(monster_gold=s.reward_gold,
                               monster_exp=s.reward_exp,
                               equipped_weapons=self._victory_weapons)
            if self.on_wincombat is not None:
                self.on_wincombat(s)
            return

        next_encounter = int(self.flags[60])
        layout = setup_encounter(next_encounter, s.party_ids,
                                 camera_origin=self.layout.camera_origin, flags=self.flags)
        self.layout = layout
        self.flags[60] = 0
        s.pending_chained_encounter = next_encounter
        s.encounter_no = next_encounter
        s.battle_message = layout.battle_message
        s.enemies.clear()
        # scr_monster_add adds active entries and calls monster initialization.
        # The old encounter's inactive monster slots are reset before reuse.
        for slot in s.monster_slots:
            hooks = self.monster_hooks.get("*")
            scr_monster_statreset(slot, hooks)
        for slot, spec in enumerate(layout.enemy_definitions):
            enemy = CombatEnemy(
                slot=slot, object_name=spec.object_name,
                monster_type=spec.monster_type,
                x=layout.camera_origin[0] + 800, y=spec.y,
                name=spec.object_name.removeprefix("obj_").removesuffix("_enemy").replace("_", " ").title(),
                entrance_target_x=spec.x, entrance_target_y=spec.y,
                entrance_frames=10,
            )
            s.enemies.append(enemy)
            hooks = self.monster_hooks.get(enemy.object_name, self.monster_hooks.get("*"))
            scr_monster_makeinstance(s.monster_slots[slot], enemy, hooks)
        s.myfight, s.mnfight = 5, -1
        s.fight_return_timer = 15
        s.reset = 0
        s.timer_alarm2 = None
        s.resolution_stage = "chained_encounter"
        s.phase = "chained_encounter"
        s.feedback = f"Encounter {next_encounter} entered; returning to commands."
        if self.on_chained_encounter is not None:
            self.on_chained_encounter(s, layout)
        if self.on_wincombat is not None:
            self.on_wincombat(s)

    def mn_end_turn(self):
        """Port scr_mnendturn: finish a *resolved* turn, or request victory.

        scr_mnendturn is called AFTER the attack/spell and bullet resolution,
        not when the player finishes choosing actions. scr_wincombat and
        scr_endturn depend on their own recovered scripts and are callback
        boundaries rather than invented enemy behavior.
        """
        s = self.state
        if s.phase in ("victory", "done", "awaiting_wincombat"):
            return

        s.susie_slot = next((i for i, cid in enumerate(s.party_ids) if cid == 2), None)
        if monster_population(s.enemies) == 0 or self.flags.get(39, 0) == 1:
            self.win_combat()
            return

        s.messagepriority = -1
        s.attackpriority = -1
        s.resolution_stage = None
        self.attack_press = None
        self.spell_phase = None
        s.simul_orders.clear()
        s.simul_total = 0
        s.hero_attack_events.clear()
        s.hero_spell_events.clear()
        for actor in s.actors:
            if actor.hero_animation is not None:
                actor.hero_animation.reset_turn()
        if self.on_cursor_memory_reset is not None:
            self.on_cursor_memory_reset(s)
        s.mnfight = 0
        s.myfight = 0
        s.bmenuno = 0
        s.charturn = 0
        s.reset = 0
        s.timer_alarm2 = None
        s.tensionselect = 0
        s.pending_option = None
        s.pending_item_slot = None
        s.pending_action_kind = None
        s.pending_heals.clear()

        # GML: with (obj_monsterparent) if end_turn_action exists, call it.
        for enemy in s.enemies:
            if enemy.active:
                hooks = self.monster_hooks.get(enemy.object_name, self.monster_hooks.get("*"))
                if hooks is not None and hooks.end_turn_action is not None:
                    hooks.end_turn_action(enemy)
                # End turn actions can alter enemy stats or remove enemies.
                s.monster_slots[enemy.slot].sync_from_enemy(enemy)

        for slot in range(3):
            s.hittarget[slot] = 0
            s.monster_slots[slot].hittarget = 0
            enemy = next((e for e in s.enemies if e.slot == slot), None)
            if enemy is not None:
                enemy.hit_target = 0
            actor = next((a for a in s.actors if a.slot == slot), None)
            if actor is None:
                continue
            actor.tu = 0
            if actor.hp is not None and actor.hp <= 0 and actor.max_hp is not None:
                amount = ceil(actor.max_hp / 8)
                # scr_heal itself has not been recovered. External implementations
                # can override the basic HP addition, including equipment effects.
                self._heal_character(actor, amount)
                s.pending_heals.append((slot, amount))
                actor.dead = actor.hp is not None and actor.hp <= 0
                s.chardead[slot] = int(actor.dead)

        s.charturn = next((actor.slot for actor in s.actors
                           if actor.can_move and not self.party_auto.get(actor.character_id, 0)), 3)

        for slot in range(3):
            s.acting_flags[slot] = 0
            s.actingsingle[slot] = 0
            s.actingsimul[slot] = 0
            s.actingtarget[slot] = 0
            s.temptension[slot] = s.tension
            s.charspecial[slot] = 0
            s.targeted[slot] = 0
            s.charaction[slot] = 0
            s.faceaction[slot] = 0
            s.monsterattackname[slot] = " "
            s.queued[slot] = None
        s.currentactingchar = 0

        for enemy in s.enemies:
            for field_name in ("attacked", "talked", "acting", "actingsus", "actingral", "actingnoe"):
                setattr(enemy, field_name, 0)
            enemy.simultotal = 0
            s.monster_slots[enemy.slot].clear_turn_flags()

        # GML scr_mnendturn refreshes tempitem indices 0..11, unlike Create's
        # 0..12 snapshot; preserve slot 12 as it was until other code changes it.
        for idx in range(12):
            for slot in range(3):
                s.tempitem[idx][slot] = self._inventory[idx]

        if s.charturn >= 3:
            # scr_endturn handles an all-AUTO/immobile party. The source also
            # specifically sets acting[0] for autonomous Susie in party slot 0.
            if s.party_ids[0] == 2 and self.party_auto.get(2, 0) == 1:
                s.acting_flags[0] = 1
                s.myfight = 3
            s.phase = "awaiting_resolution"
            self.end_turn()
        else:
            s.phase = "command"
            s.feedback = ""

    def reset_turn(self):
        """Compatibility entry: next turn after action resolution."""
        s = self.state
        if s.phase not in ("awaiting_resolution", "enemy_turn"):
            raise RuntimeError("Cannot start next turn before actions resolve")
        self.mn_end_turn()

    def begin_enemy_turn(self, duration: int = 120):
        """Enter bullet phase; generating bullets remains an enemy event."""
        s = self.state
        s.phase = "enemy_turn"
        s.mnfight = 2
        s.turntimer = max(0, int(duration))
        s.reset = 0
        s.timer_alarm2 = None

    def update(self, frames: int = 1):
        """Step the screen and battle timers, not any invented enemy AI."""
        s = self.state
        for _ in range(max(0, int(frames))):
            # Snapshot before phase/Hero Step: GameMaker does not Step a new
            # instance on the very frame its creator spawned it.
            active_rudebusters = tuple(self.rudebuster_animations)
            active_bolts = tuple(self.rudebuster_bolts)
            if s.phase == "awaiting_resolution":
                if s.resolution_stage == "attack_press" and self.attack_press is not None:
                    self.attack_press.advance()
                elif s.resolution_stage == "spell_phase" and self.spell_phase is not None:
                    self.spell_phase.advance()
            # Step hero objects *after* phase objects: newly triggered attacks
            # become active in this frame, then count down independently.
            for actor in s.actors:
                if actor.hero_animation is not None:
                    actor.hero_animation.step(
                        s, resolve_attack=self._resolve_hero_attack,
                        resolve_spell=self._resolve_hero_spell,
                        on_sound=self.on_hero_sound)
            # Projectiles are stepped from a start-of-frame snapshot.  A bolt
            # born during obj_rudebuster_anim t=10 starts on the NEXT frame.
            for anim in active_rudebusters:
                anim.step()
            for bolt in active_bolts:
                bolt.step()
            self.rudebuster_animations = [a for a in self.rudebuster_animations if a.alive]
            self.rudebuster_bolts = [b for b in self.rudebuster_bolts if b.alive]
            if s.phase == "chained_encounter":
                for enemy in s.enemies:
                    if enemy.entrance_frames > 0 and enemy.entrance_target_x is not None:
                        enemy.x += (enemy.entrance_target_x - enemy.x) / enemy.entrance_frames
                        enemy.y += (enemy.entrance_target_y - enemy.y) / enemy.entrance_frames
                        enemy.entrance_frames -= 1
                        s.monster_slots[enemy.slot].sync_from_enemy(enemy)
                s.fight_return_timer -= 1
                if s.fight_return_timer <= 0:
                    # GML Step myfight==5 calls scr_mnendturn here.
                    # Prevent erroneously triggering victory if next wave is
                    # truly empty (encounters normally supply 1..3 enemies).
                    s.myfight = 5
                    self.mn_end_turn()
            if s.intro == 1:
                if s.bp < s.bpy - 1:
                    diff = s.bpy - s.bp
                    s.bp += floor(diff / 2.5 + 0.5) if diff < 40 else 30
                else:
                    s.bp = s.bpy
                if s.bp >= s.bpy:
                    s.bp, s.intro = s.bpy, 0
            elif s.intro == 2:
                s.bp = max(0, s.bp - 30)
                if s.bp == 0:
                    s.intro = 3
            if s.phase == "victory":
                s.victortimer += 1
                if s.victortimer >= 10 and s.victory_message_dismissed:
                    s.intro = 2
                    if s.bp == 0:
                        s.phase = "done"
                        if not self._finished_callback_called and self.on_victory_finished:
                            self._finished_callback_called = True
                            self.on_victory_finished(s)
            # Alarm[2] is counted on subsequent frames, not on its
            # scheduling frame; its event calls scr_mnendturn.
            if s.timer_alarm2 is not None:
                s.timer_alarm2 -= 1
                if s.timer_alarm2 <= 0:
                    s.timer_alarm2 = None
                    s.reset = 0
                    self.mn_end_turn()
            elif s.mnfight == 2 and s.timeron and s.reset == 0:
                s.turntimer -= 1
                if s.turntimer <= 0:
                    s.reset = 1
                    s.timer_alarm2 = 15

    def begin_victory(self, *, monster_gold: int = 0, monster_exp: int = 0,
                      skipvictory: int = 0, equipped_weapons: Mapping[int, int] | None = None,
                      armor_counts: Mapping[int, int] | None = None,
                      level_up: Callable[[], None] | None = None):
        """Port the normal victory reward formula; call only on *real* victory.

        armor_counts represents scr_armorcheck_equipped_party results; we never
        assume which Dark World armor is equipped based on Light World armor.
        """
        s = self.state
        if s.victoried:
            return
        s.victory = s.victoried = 1
        s.battleend = 1
        s.mnfight = -1
        s.myfight = 7
        s.phase = "victory"
        s.skipvictory = skipvictory
        s.faceaction = [0] * 3
        for actor in s.actors:
            if actor.hp is not None and actor.max_hp is not None and actor.hp < 1:
                actor.hp = floor(actor.max_hp / 8 + 0.5)
            actor.state = 7
        if skipvictory == 0:
            amount = float(monster_gold) + floor(s.tension / 10) * s.chapter
            weapons = equipped_weapons or {}
            for weapon in (8, 53):
                if weapons.get(1) == weapon:
                    amount += floor(amount / 20)
            armor = armor_counts or {}
            amount *= 1 + armor.get(8, 0) * 0.05
            amount *= 1 + armor.get(21, 0) * 0.3
            amount -= amount * armor.get(54, 0) * 0.1
            amount = max(0, amount - amount * armor.get(32, 0) * 0.9)
            reward = 0 if self.flags.get(37, 0) == 1 else floor(amount)
            s.reward_gold = reward
            s.reward_exp = int(monster_exp)
            s.gold = max(0, s.gold + reward)
            s.xp += int(monster_exp)
            s.fc = s.fe = 0
            s.victory_message = f"* You won!\n* Got {s.reward_exp} EXP and {reward} D$."
            if self.flags.get(37, 0) == 1:
                s.victory_message = "* You won the battle!"
            if self.flags.get(63, 0) == 1:
                who = "Noelle became stronger." if s.havechar[3] else "You became stronger."
                s.victory_message = f"* You won!\n* Got {reward} D$.\n* {who}"
                if level_up:
                    level_up()
        s.victortimer = (-20 if skipvictory == 1 else 9 if skipvictory == 2 else 0)
        if skipvictory:
            s.victory_message_dismissed = True
        s.intro = 2 if skipvictory else 0
