# Chapter 6 battle system — `obj_rudebuster_bolt` port

This update builds on `deltarune_ch6_damage_rudebuster_update.zip` and is a complete replacement bundle, not a patch that requires earlier ZIP files.

## What was recovered

The supplied GML included the Create, Step, and Draw events for `obj_rudebuster_bolt`. The Draw event consists of `draw_self()`, so the provisional Tkinter view represents the sprite with vector shapes; the source sprite sheet is still needed for a pixel-exact appearance.

### Create, movement, and timing

- `RudeBusterBolt` in `battle_effects.py` stores the original spell caster, enemy slot, damage, red variant, stage position, movement, impact and animation fields.
- On the first Step (`t == 0`), capture enemy position, aim at the enemy with a **-20°** offset, set speed to **24**, and set friction to **-1.5** (so speed increases by 1.5 per tick). RED BUSTER uses its red beam/sizes.
- Subsequent steps steer by a quarter of the normalized angle difference and check for impact when within **40 GML pixels** of the captured point. Movement is calculated in the GameMaker direction convention (90° = up).
- `button1_p()` is mapped to **Z**, **Enter**, or **Space**. Once the bolt timer reaches **4**, the first eligible press locks `chosen_bolt`; further presses cannot replace the choice.
- At impact, `final_bolt` is the current timer. When `final_bolt - chosen_bolt` equals 0/1/2/3/4/5/6, award **30/28/22/20/13/11/10** bonus damage, respectively. A press farther away has no bonus. A difference with absolute magnitude ≤2 requests the special burst sound and visual. These bonuses are added once.
- If `obj_trashy_trio` is present, the damage is first reduced to `ceil(damage * 0.1)`. If this is a RED BUSTER bolt, **90 damage is added after** that reduction.
- Only when the projectile enters the impact state does it call `BattleCombatController.damage_enemy`, resetting this target's hit counter first. That existing script handles damage writers, HP, callbacks, hit/dodge effects, and defeat flags. `obj_trashy_trio` restores the target's pre-hit HP after the strike and sets its `back` timer to 30. A pink-enemy presence zeros all logical damage-writer numbers (not HP), matching `with(obj_dmgwriter)`.
- The bolt creates eight logical radial burst particles, with the recovered 0.75 / 0.8 speed decays and 0.8 x-scale multiplier, and destroys itself at explosion `t >= 18`. Pre-impact trails fade and shrink.

### Controller + renderer integration

- `BattleCombatController._emit_spell_animation` turns the existing `obj_rudebuster_bolt` request into an active `RudeBusterBolt`. Its parent `obj_rudebuster_anim` still creates the request on **t == 10** and restores Susie on **t >= 28**.
- Controller update uses a **start-of-frame snapshot**, so newly spawned bolts don't Step on their creation frame.
- Controller input also reaches live bolts during spell-phase animation; keyboard inputs remain wired through `Game.key_press`.
- `BattleCanvasView` renders an approximate beam, afterimage trail, and impact burst. Rendering is intentionally read-only.
- Optional existing `on_hero_sound` callbacks receive the recovered `snd_scytheburst`, `snd_rudebuster_hit`, `snd_bounceflower`, and `snd_acquire_lancer` names. The game only plays a file if that sound asset exists.

## Dependencies / limitations

- `scr_afterimage`, `scr_oflash`, `obj_dmgwriter` sprites, `spr_rudebuster_beam`, `spr_rudebuster_beam_red`, and `obj_rudebuster_bolt`'s real assets are not supplied; their logical events or simple renderer shapes stand in.
- Special scene-object visual overrides for yellow/blue, pink, and Flowery are still proxies or existing callbacks, not reconstructed enemy scene choreography. The blue/yellow interception target mapping from `obj_rudebuster_anim` is retained.
- Nonbattle bolts don't alter battle HP. A target already removed from the logical monster roster isn't damaged on impact. Unknown HP remains unknown.
- The original GML's `obj_trashy_trio` restore occurs **after** `scr_damage_enemy`; its interactions with a lethally low HP value and defeat bookkeeping are unusual in the original source too. Do not treat this as full Trashy Trio AI.
- Homing and animation advance on the fangame's nominal 60-Hz game loop. Authentic GameMaker engine instance/event ordering can differ by a tick in unusual cases, so real-asset playtesting is still recommended.

## Installation

Extract `deltarune_ch6_rudebuster_bolt_update.zip` into your Python fangame's source folder, replacing `battle_effects.py`, `battle_combat.py`, and `battle_view.py`. The ZIP contains the other compatible battle files and `game.py` as well.

## Verification

```bash
python -m compileall -q game.py battle*.py encounter_setup.py
python -m unittest discover -p 'test_*.py' -q
```

Result in the integration workspace: **252 tests passed**, including **24 new `obj_rudebuster_bolt` tests**. Tkinter asset-accurate testing has not been performed.
