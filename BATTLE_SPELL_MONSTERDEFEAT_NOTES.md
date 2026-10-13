# Deltarune Chapter 6 Python — `scr_spell` and `scr_monsterdefeat`

This update builds on the `obj_heroparent` release. Replace the included battle/game modules together. The original game assets, GUI support files, and sprite sheets are not included.

## Source-backed behavior

`battle_spells.py` ports the recovered `scr_spell(arg0, arg1)` switch, keeping spell and item IDs unchanged. The 16-tick `obj_heroparent` spell callback now **actually invokes** this module (as well as the existing `on_spell_effect` extension callback). It records each execution as `CombatState.spell_effect_outcomes` and, when needed, emits `SpellAnimationRequest` values.

- **Immediate damage:** spell 1 (RUDE BUSTER) calculates `ceil(AT * 10 - monster DF * 3)`, respects `automiss`, and updates enemy HP through `BattleCombatController.damage_enemy()`. This provides the basic HP consequence of `scr_damage_enemy`; extra effects from the missing `scr_damage_enemy` script aren't assumed.
- **Healing:** HEAL PRAYER (2), DUAL HEAL (6), Chapter 5 HEAL (11), and item IDs 201–243 and 260–270 are handled according to the supplied switch. Conditional healing (character favorite items), revival quantities, all-party healing, and S.POISON's 60-tick poison state are included. `scr_heal_amount_modify_by_equipment` is not supplied; `on_spell_heal_modifier` defaults to the unmodified amount and can be registered later.
- **Pacify/spare:** spell 3 handles TIRED enemies and per-monster exceptions; spell 100 checks MERCY, adds `spare_point` for failed SPARE, handles exceptions for monster types 3/52, and invokes the recovered monster-defeat handling on success.
- **Animation-owned effects:** spells 4/5 (RUDE/RED BUSTER animations), 8 (SLEEPMIST), 9 (ICESHOCK), 10 (SNOWGRAVE), 12 (REVIVESONG), and 13 (SCYTHEMARE) emit animation requests with source-backed parameters (damage/heal where calculable, target, staggered delay). **These requests do not automatically change enemy HP, apply TIRED/frozen status, or revive party members.** The corresponding GameMaker animation-object scripts must be recovered to implement those follow-on effects accurately. `obj_pacifyspell` visuals likewise remain optional.
- **IDs with no effect in `scr_spell`:** the switch has deliberate empty cases for several items, including GLOWSHARD and MANUAL; their effects are in the previously ported `scr_spelltext`. No unsupported fallback effects are invented.

`battle_monsters.py` now contains a full `scr_monsterdefeat` port called through `BattleCombatController.defeat_enemy(slot, outcome=None, call_user10=False)`. It:

1. Adds the defeated monster's gold and EXP **once** to the battle reward accumulators.
2. Computes `flag[51 + slot]` disposition when not already set: `1` for HP defeat, otherwise `2` for spared/removed.
3. Updates outcome counters `flag[40]` (violent), `[41]` (spared), `[42]` (pacified), `[43]` (automated), `[45]` (frozen), `[44]` (fatal), and the `+24` gold bonus for frozen results.
4. On the last enemy, applies original outcome priority **frozen → pacified → spared → violent**, with later matches winning, and updates `flag[50]`, optional `flag[926]`, and completion destination `flag[flag[54]]` before zeroing `flag[54]`.
5. Invokes enemy User[11] at the end. A successful PACIFY/SPARE calls User[10] first. The old `MonsterHooks.monster_defeat` callback remains as a backwards-compatible post-defeat hook.

The existing **FIGHT** lethal-hit path and both `scr_wincombat` branches now use this centralized defeat routine, preventing double reward collection.

## Hook interfaces

```python
from battle_combat import BattleCombatController
from battle_monsters import MonsterHooks

controller = BattleCombatController(
    layout, (1, 2, 3), flags,
    party_stats={1:{"attack": 12, "magic": 4, "hp": 90, "max_hp": 90}},
    equipped_armors={3: (36,)},
    monster_hooks={"obj_baseenemy": MonsterHooks(
        event_user_10=lambda enemy: None,
        event_user_11=lambda enemy: None,
    )},
    on_spell_animation=lambda state, request: print(request),
    on_spell_heal_modifier=lambda amount, state, caster_slot: amount,
)
# If enemy stats are supplied by the real User[12]/User[15] handlers:
controller.set_enemy_stats(0, hp=150, max_hp=150, defense=5)
controller.state.chartarget[0] = 0
outcome = controller.scr_spell(1, 0)
```

The same hooks can be set on `Game` before battle initiation as `battle_spell_animation_callback` and `battle_spell_heal_modifier_callback`. The existing `battle_spell_effect_callback` continues to receive notifications after built-in spell handling. Enemy-specific User Event 12/15, animated spell hit results, `scr_healitemspell` visual effects, and accurate combat sprite rendering still depend on additional source/assets.

## Testing

Run from the extracted directory:

```sh
python -m unittest discover -p 'test_*.py' -q
python -m py_compile battle.py battle_combat.py battle_heroes.py battle_monsters.py battle_phases.py battle_spelltext.py battle_spells.py battle_view.py encounter_setup.py game.py
```

**208 headless tests pass** as of this release, including 22 source-specific effect/defeat tests. Full Tk runtime and source asset testing have not been performed: the remaining game modules and assets are not part of this isolated package.
