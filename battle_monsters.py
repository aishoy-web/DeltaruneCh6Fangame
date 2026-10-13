"""Battle monster slot lifecycle port, without inventing enemy object scripts.

GameMaker performs scr_monster_statreset for all three slots, then calls
scr_monster_makeinstance on occupied slots. An actual enemy's User[12] and
User[15] events supply its statistics and AI setup. Register those events
here as Python callables as individual enemy implementations are recovered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from battle_combat import CombatEnemy


@dataclass(slots=True)
class MonsterSlotState:
    """Values cleared by scr_monster_statreset (one of three GML slots)."""
    index: int
    monster: int = 0
    monsterx: float = 0
    monstery: float = 0
    monstername: str = " "
    monsterat: int = 0
    monsterdf: int = 0
    monsterhp: int = 0
    monstermaxhp: int = 0
    monsterinstance: CombatEnemy | None = None
    monstergold: int = 0
    monsterexp: int = 0
    sparepoint: int = 0
    hittarget: int = 0
    mercymod: float = 0
    mercymax: float = 0
    monstercomment: str = " "
    monsterattackname: str = " "
    monsterstatus: int = 0
    # Per-enemy turn flags reset by scr_mnendturn.
    attacked: int = 0
    talked: int = 0
    acting: int = 0
    actingsus: int = 0
    actingral: int = 0
    actingnoe: int = 0

    def reset(self):
        """scr_monster_statreset; never transfers old instance data."""
        self.monster = 0
        self.monsterx = self.monstery = 0
        self.monstername = " "
        self.monsterat = self.monsterdf = 0
        self.monsterhp = self.monstermaxhp = 0
        self.monsterinstance = None
        self.monstergold = self.monsterexp = 0
        self.sparepoint = self.hittarget = 0
        self.mercymod = self.mercymax = 0
        self.monstercomment = self.monsterattackname = " "
        self.monsterstatus = 0
        self.clear_turn_flags()

    def clear_turn_flags(self):
        for name in ("attacked", "talked", "acting", "actingsus", "actingral", "actingnoe"):
            setattr(self, name, 0)

    def sync_from_enemy(self, enemy: CombatEnemy):
        """Mirror only known enemy data; unknown values stay at reset defaults.

        A zero-valued GML stat reset is NOT proof that an enemy has zero HP.
        The visible CombatEnemy continues to use None for unknown HP.
        """
        self.monster = int(enemy.active)
        self.monsterx, self.monstery = enemy.x, enemy.y
        self.monstername = enemy.name if enemy.stats_loaded else " "
        self.monsterat = enemy.attack if enemy.attack is not None else 0
        self.monsterdf = enemy.defense if enemy.defense is not None else 0
        self.monsterhp = enemy.hp if enemy.hp is not None else 0
        self.monstermaxhp = enemy.max_hp if enemy.max_hp is not None else 0
        self.monstergold, self.monsterexp = enemy.gold, enemy.exp
        self.sparepoint = enemy.spare_point
        self.hittarget = enemy.hit_target
        self.mercymod = enemy.mercy if enemy.mercy is not None else 0
        self.mercymax = (enemy.mercy_max if enemy.stats_loaded and enemy.mercy_max is not None else 0)
        self.monstercomment, self.monsterattackname = enemy.comment, enemy.attack_name
        self.monsterstatus = enemy.status


@dataclass(slots=True)
class MonsterHooks:
    """Explicit replacements for GameMaker monster events, by object name.

    act_reset is called with the zeroed MonsterSlotState; other handlers
    receive the instantiated CombatEnemy and may set stats, ACTs, etc.
    """
    act_reset: Callable[[MonsterSlotState], None] | None = None
    event_user_12: Callable[[CombatEnemy], None] | None = None
    event_user_15: Callable[[CombatEnemy], None] | None = None
    end_turn_action: Callable[[CombatEnemy], None] | None = None
    monster_defeat: Callable[[CombatEnemy], None] | None = None
    # obj_heroparent calls enemy.callback_on_damage(id) after reducing HP.
    on_damage: Callable[[CombatEnemy, object, int], None] | None = None
    # Added after prior fields to preserve positional MonsterHooks compatibility.
    event_user_10: Callable[[CombatEnemy], None] | None = None
    event_user_11: Callable[[CombatEnemy], None] | None = None


def scr_monster_statreset(slot: MonsterSlotState, hooks: MonsterHooks | None = None):
    slot.reset()
    if hooks is not None and hooks.act_reset is not None:
        hooks.act_reset(slot)


def scr_monster_makeinstance(slot: MonsterSlotState, enemy: CombatEnemy,
                             hooks: MonsterHooks | None = None):
    """Instantiate at spawn position; invoke User[12], then User[15]."""
    # The controller creates a new CombatEnemy per encounter. Replace the
    # previous logical instance if this slot is deliberately recreated.
    if slot.monsterinstance is not None and slot.monsterinstance is not enemy:
        slot.monsterinstance.active = False
    slot.monster = 1
    slot.monsterinstance = enemy
    enemy.active = True
    # The new instance was constructed using monstermakex/y.
    enemy.slot = slot.index  # Equivalent to `myself = arg0`.
    previous_name = enemy.name  # The temporary object-name stand-in.
    if hooks is not None and hooks.event_user_12 is not None:
        hooks.event_user_12(enemy)
    if hooks is not None and hooks.event_user_15 is not None:
        hooks.event_user_15(enemy)
    if (enemy.hp is not None or enemy.max_hp is not None or
        enemy.attack is not None or enemy.defense is not None or
        enemy.mercy is not None or enemy.name != previous_name):
        enemy.stats_loaded = True
    slot.sync_from_enemy(enemy)


def monster_population(enemies) -> int:
    """scr_monsterpop's useful observable outcome: number of live slots."""
    return sum(1 for enemy in enemies if enemy.active)


def scr_monsterdefeat(enemy: CombatEnemy, state, flags, hooks: MonsterHooks | None = None,
                      *, call_user10: bool = False) -> bool:
    """Port the whole scr_monsterdefeat reward and flag bookkeeping.

    The monster owns its slot (`myself`). Repeated defeat calls do nothing.
    User[10] belongs to PACIFY/SPARE, before this function; User[11] is
    invoked at the end of this function, just as in the source.
    """
    slot = enemy.slot
    if not enemy.active or not 0 <= slot < 3:
        return False
    if call_user10 and hooks is not None and hooks.event_user_10 is not None:
        hooks.event_user_10(enemy)
    state.reward_gold += enemy.gold
    state.reward_exp += enemy.exp
    enemy.active = False

    disposition_key = 51 + slot
    outcome = flags.get(disposition_key, 0)
    if outcome == 0:
        outcome = 1 if enemy.hp is not None and enemy.hp <= 0 else 2
        flags[disposition_key] = outcome
    counters = {1: 40, 2: 41, 3: 42, 5: 43, 6: 45}
    if outcome in counters:
        key = counters[outcome]
        flags[key] = flags.get(key, 0) + 1
    if outcome == 1 and enemy.fatal == 1:
        flags[44] = flags.get(44, 0) + 1
    if outcome == 6:
        state.reward_gold += 24
    if monster_population(state.enemies) == 0:
        # Priority order from the GML, applied in sequence:
        # frozen -> pacified -> spared -> violent (last matching wins).
        final = flags.get(50, 0)
        for designation, code in ((6, 6), (3, 3), (2, 2), (1, 1)):
            if any(flags.get(51 + i, 0) == designation for i in range(3)):
                final = code
        flags[50] = final
        if final == 6:
            flags[926] = flags.get(926, 0) + 1
        tracked_key = flags.get(54, 0)
        if tracked_key != 0:
            flags[tracked_key] = final
            flags[54] = 0
    state.monster_slots[slot].sync_from_enemy(enemy)
    if hooks is not None:
        if hooks.event_user_11 is not None:
            hooks.event_user_11(enemy)
        # Existing hook supported by prior releases; now means the complete
        # defeat script has run, instead of being the script itself.
        if hooks.monster_defeat is not None:
            hooks.monster_defeat(enemy)
    return True
