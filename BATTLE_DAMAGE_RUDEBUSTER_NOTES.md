# Chapter 6 Python battle system — `scr_damage_enemy` + `obj_rudebuster_anim`

This update builds on **deltarune_ch6_spell_monsterdefeat_update.zip**. The new `battle_effects.py` module is imported from the updated `battle_combat.py`. The existing `game.py` already constructs that controller; no new Game constructor arguments are necessary.

## Recovered `scr_damage_enemy(arg0, arg1)`

`BattleCombatController.damage_enemy(slot, amount, caster_slot)` / `scr_damage_enemy` now:

1. Creates a logical `obj_dmgwriter` record in `state.damage_writer_events` at `(enemy.x, enemy.y + 20 - hittarget[slot] * 20)` **before** mutating enemy HP. `DamageWriterEvent` stores the original damage, optional `type`, and `delay`.
2. Sets writer type to party character ID minus one, except Noelle uses 6; `caster_slot == 5` uses type 5.
3. Subtracts the original signed damage value from known enemy HP. This script has **no minimum-zero clamp**; it is not the same formula as the regular hero FIGHT routine.
4. Calls the registered `MonsterHooks.on_damage(enemy, actor, amount)` after HP subtraction but before the hit reaction. Callbacks can alter HP and prevent an otherwise lethal hit.
5. For positive damage sets `shakex=9`, monster `state=3`, `hurttimer=30`, and `hurtamt=amount`.
6. Increments the per-monster `hittarget` counter. For zero damage sets `hurtamt=0` and, if `hurttimer<=15` and `candodge==1`, enters dodge state 4 with `dodgetimer=0`.
7. When HP is still at or below zero after the callback, invokes our port of `scr_monsterdefeat` exactly once, preserving gold/EXP and outcome flags.

The existing `scr_spell` case 1 now sets the newly created damage-writer record's `delay` to 8, matching its `dm.delay=8` assignment. Other `obj_dmgwriter` sprite logic remains pending. When monster HP is unspecified, the method returns `None` without inventing a value.

## Recovered `obj_rudebuster_anim` Create/Step

- Spells 4 and 5 still compute their source formulas in `battle_spells.py` and emit `SpellAnimationRequest('obj_rudebuster_anim', ...)`.
- The controller now creates a `RudeBusterAnimation` instance for that request. It captures Susie's battle position and hides Susie (when present). If Susie is absent, it enters non-battle mode without hiding a hero.
- The animation uses `image_index = t / 2`. On its Step when **`t == 10`** (the 11th Step), it emits `SpellAnimationRequest('obj_rudebuster_bolt', ...)` with the original damage, caster, enemy slot, `red` flag, and projectile spawn position `(animation.x+40, animation.y+30)`; it also invokes the optional hero SFX callback with `snd_rudebuster_swing`.
- If active `obj_blue_enemy` and `obj_yellow_enemy` instances coexist, their recovered intercept/`yellowbluecon` branch updates position, target, and the projectile request's extra fields.
- At `t >= 28` (the 29th Step), it restores Susie's visibility and destroys the logical animation object.
- New animation objects do not receive a Step on their creation frame. Drawing stays read-only; the provisional Tk view suppresses hidden Susie and shows an animation title.

**Important boundary:** `obj_rudebuster_bolt`'s Step/Collision/Draw and hit effects have **not** been provided. Creating a bolt request does not damage enemies automatically. This prevents applying delayed damage prematurely or twice. The bolt request goes through the existing `on_spell_animation(state, request)` callback, and all emitted requests are recorded as `state.spell_animation_events`. Implement that projectile using the actual GML object events when supplied.

## Install

Extract the provided ZIP over your existing Python game source, replacing `battle_combat.py`, `battle_spells.py`, and `battle_view.py`; add `battle_effects.py`. `game.py`, `battle_heroes.py`, and other modules are included for convenience.

## Testing

```
python -m compileall -q game.py battle*.py encounter_setup.py
python -m unittest discover -p 'test_*.py' -q
```

The test suite validates writer stacking, Noelle/caster-5 writer types, source callback ordering, dodges, negative damage, lethal defeat, the t=10 projectile emission, the t=28 cleanup, the blue/yellow intercept, and a hero spawning an animation partway through a frame. Test mode is headless; asset-perfect sprite rendering and the projectile object remain outstanding.
