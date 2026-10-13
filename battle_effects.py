"""Recovered scr_damage_enemy, obj_rudebuster_anim and obj_rudebuster_bolt.

The bolt owns damage-on-impact, movement, timing bonuses, and logical trails.
Stage positions use original 640x480 GameMaker coordinates; unavailable sprite
objects are represented as simple view effects rather than guessed AI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from battle_spells import SpellAnimationRequest

if TYPE_CHECKING:
    from battle_combat import BattleCombatController


@dataclass(slots=True)
class DamageWriterEvent:
    """obj_dmgwriter instance parameters set by scr_damage_enemy."""
    enemy_slot: int
    x: float
    y: float
    damage: int
    type: int | None = None
    delay: int = 0   # obj_dmgwriter Create defaults are not provided


@dataclass(slots=True)
class RudeBusterAnimation:
    """Frame-by-frame port of obj_rudebuster_anim Create and Step.

    `t` increments *after* each Step, matching GameMaker. At t==10 create
    obj_rudebuster_bolt; at t>=28 show Susie and destroy the parent.
    """
    controller: BattleCombatController
    caster_slot: int
    star: int
    damage: int
    red: int = 0
    x: float = 0.0
    y: float = 0.0
    t: int = 0
    alive: bool = True
    battlemode: int = 0
    image_index: float = 0.0
    projectile_fired: bool = False
    susie_actor_slot: int | None = None

    @classmethod
    def from_request(cls, controller: BattleCombatController,
                     req: SpellAnimationRequest) -> "RudeBusterAnimation":
        extras = dict(req.extra)
        susie = next((a for a in controller.state.actors if a.character_id == 2), None)
        source_actor = susie or next((a for a in controller.state.actors
                                      if a.slot == req.caster_slot), None)
        instance = cls(
            controller=controller, caster_slot=req.caster_slot,
            star=int(req.target_slot) if req.target_slot is not None else -1,
            damage=int(req.damage) if req.damage is not None else 0,
            red=int(extras.get('red', 0)),
            x=source_actor.x if source_actor is not None else 0,
            y=source_actor.y if source_actor is not None else 0,
            battlemode=int(susie is not None),
            susie_actor_slot=susie.slot if susie is not None else None,
        )
        if susie is not None:
            susie.visible = False
        return instance

    def step(self) -> None:
        if not self.alive:
            return
        self.image_index = self.t / 2
        if self.t >= 28:
            self.finish()
            return

        controller = self.controller
        state = controller.state
        target = next((e for e in state.enemies if e.slot == self.star and e.active), None)
        if target is not None and self.t == 10:
            new_target = self.star
            props: dict[str, object] = {
                'x': self.x + 40, 'y': self.y + 30,
                'red': self.red, 'battlemode': self.battlemode,
            }
            # obj_yellow_enemy + obj_blue_enemy special intercept.
            blue = next((e for e in state.enemies if e.active and
                         e.object_name == 'obj_blue_enemy'), None)
            yellow = next((e for e in state.enemies if e.active and
                           e.object_name == 'obj_yellow_enemy'), None)
            if yellow is not None and blue is not None:
                susie_slot = self.susie_actor_slot
                if (susie_slot is not None and state.chartarget[susie_slot] == blue.slot):
                    yellow.blockcon = 1
                    yellow.blocktimer = 0
                    yellow.hurtsprite = 'spr_yellow_block'
                    yellow.x, yellow.y = blue.x - 60, blue.y
                    # GML targets sentinel 171; star remains a monster slot.
                    props['instance_target'] = 171
                    props['intercepted_blue'] = True
                    new_target = yellow.slot
                    state.chartarget[susie_slot] = yellow.slot
                    state.monster_slots[yellow.slot].sync_from_enemy(yellow)
                else:
                    props['yellowbluecon'] = 1
            projectile = SpellAnimationRequest(
                'obj_rudebuster_bolt', self.caster_slot, new_target,
                damage=self.damage, extra=tuple(props.items()),
            )
            controller._emit_spell_animation(projectile)
            self.projectile_fired = True
            controller._notify_battle_sound('snd_rudebuster_swing', 1.0)
        self.t += 1

    def finish(self) -> None:
        if self.susie_actor_slot is not None:
            actor = next((a for a in self.controller.state.actors
                          if a.slot == self.susie_actor_slot), None)
            if actor is not None:
                actor.visible = True
        self.alive = False


@dataclass(slots=True)
class RudeBusterTrail:
    """One logical scr_afterimage (the original sprite is asset-dependent)."""
    x: float
    y: float
    angle: float
    alpha: float
    yscale: float = 1.8

    def step(self, exploding: bool) -> bool:
        self.yscale -= 0.1
        if exploding:
            self.alpha -= 0.07
            self.yscale *= 0.9
        return self.yscale > 0.1


@dataclass(slots=True)
class RudeBusterBurst:
    """Eight radial afterimages created on the projectile's impact frame."""
    angle: float
    speed: float
    xscale: float = 2.0
    yscale: float = 2.0

    def step(self, index: int) -> None:
        self.speed *= 0.75 if index < 4 else 0.8
        self.xscale *= 0.8


@dataclass(slots=True)
class RudeBusterBolt:
    """obj_rudebuster_bolt Create/Step; Draw is handled by BattleCanvasView.

    Uses GameMaker coordinates (angle 0=right, angle 90=up) and 60-Hz
    discrete steps.  The impact is processed only after homing movement has
    brought the bolt within 40 pixels of its captured target position.
    """
    controller: BattleCombatController
    caster_slot: int
    star: int
    damage: int
    x: float
    y: float
    red: int = 0
    battlemode: int = 1
    yellowbluecon: int = 0
    t: int = 0
    alive: bool = True
    image_alpha: float = 0.0
    image_xscale: float = 2.0
    image_yscale: float = 2.0
    image_speed: float = 1.0
    image_angle: float = 0.0
    image_index: float = 0.0
    tmax: int = 4  # recovered Create state; not read by this Step event
    siner: float = 0.0
    a: int = 0
    maxaft: int = 0
    prevx: list[float] = field(default_factory=list)
    prevy: list[float] = field(default_factory=list)
    visible: bool = True
    direction: float = 0.0
    speed: float = 0.0
    friction: float = -1.5
    targetx: float = 0.0
    targety: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    explode: int = 0
    bolt_timer: int = 0
    chosen_bolt: int = 0
    final_bolt: int = 0
    lockdamage: bool = False
    bonus_anim: int = 0
    impact_damage: int | None = None
    impact_processed: bool = False
    image_sprite: str = 'spr_rudebuster_beam'
    trails: list[RudeBusterTrail] = field(default_factory=list)
    bursts: list[RudeBusterBurst] = field(default_factory=list)
    _press: bool = False

    @classmethod
    def from_request(cls, controller: BattleCombatController,
                     request: SpellAnimationRequest) -> "RudeBusterBolt":
        extras = dict(request.extra)
        bolt = cls(
            controller=controller,
            caster_slot=request.caster_slot,
            star=request.target_slot if request.target_slot is not None else -1,
            damage=int(request.damage) if request.damage is not None else 0,
            x=float(extras.get('x', 0)), y=float(extras.get('y', 0)),
            red=int(extras.get('red', 0)),
            battlemode=int(extras.get('battlemode', controller.state.fighting != 0)),
            yellowbluecon=int(extras.get('yellowbluecon', 0)),
        )
        bolt.prevx = [bolt.x] * 10
        bolt.prevy = [bolt.y] * 10
        return bolt

    def button(self, key: str) -> None:
        """button1_p() edge, buffered until the next logical Step."""
        if key.lower() in ('z', 'return', 'space') and self.alive and not self.explode:
            self._press = True

    @staticmethod
    def _direction(x: float, y: float, dest_x: float, dest_y: float) -> float:
        from math import atan2, degrees
        return degrees(atan2(y - dest_y, dest_x - x)) % 360

    @staticmethod
    def _difference(target: float, current: float) -> float:
        return ((target - current + 180) % 360) - 180

    def _target(self):
        return next((e for e in self.controller.state.enemies if e.slot == self.star), None)

    def _initial_step(self) -> None:
        target = self._target()
        if target is not None:
            # In battle, the global.monsterx/y arrays mirror the logical enemy
            # position; this also supports the blue/yellow interception target.
            self.targetx, self.targety = target.x, target.y
        self.cx, self.cy = self.targetx, self.targety
        self.direction = (self._direction(self.x, self.y, self.cx, self.cy) - 20) % 360
        self.image_angle = self.direction
        self.speed = 24
        self.friction = -1.5
        if self.red:
            self.image_sprite = 'spr_rudebuster_beam_red'
            self.image_xscale = self.image_yscale = 2.5

    def _award_bonus(self) -> None:
        # The source only rewards the first button1_p after bolt_timer >= 4.
        if self.chosen_bolt > 0:
            difference = self.final_bolt - self.chosen_bolt
            self.damage += {0: 30, 1: 28, 2: 22, 3: 20,
                            4: 13, 5: 11, 6: 10}.get(difference, 0)
            if abs(difference) <= 2:
                self.bonus_anim = 1
                self.controller._notify_battle_sound('snd_scytheburst', 1.0)

    def _impact(self) -> None:
        if self.impact_processed:
            return
        self.impact_processed = True
        self._award_bonus()
        state = self.controller.state
        trashy = next((e for e in state.enemies
                       if e.object_name == 'obj_trashy_trio' and e.active), None)
        original_hp = None
        target = self._target()
        if trashy is not None:
            from math import ceil
            self.damage = ceil(self.damage * 0.1)
            if target is not None:
                original_hp = target.hp
        # The RED variant adds +90 *after* the obj_trashy_trio reduction.
        if self.red:
            self.damage += 90
        self.impact_damage = self.damage
        if self.battlemode and target is not None and target.active:
            state.hittarget[self.star] = 0
            target.hit_target = 0
            self.controller.damage_enemy(self.star, self.damage, self.caster_slot)
            # The GML sprite override applies to damage writers, not HP.
            if any(e.object_name == 'obj_pink_enemy' and e.active
                   for e in state.enemies):
                # GML `with (obj_dmgwriter) damage = 0` affects EVERY writer,
                # and is not gated by chapter.
                for writer in state.damage_writer_events:
                    writer.damage = 0
            if trashy is not None and original_hp is not None:
                # obj_trashy_trio specifically restores the pre-hit HP.
                target.hp = original_hp
                target.active = True
                state.monster_slots[target.slot].sync_from_enemy(target)
                trashy.blockcon = 1
                trashy.back = 30
                self.controller._notify_battle_sound('snd_bounceflower', 1.0)
                self.controller._notify_battle_sound('snd_acquire_lancer', 1.0)
            else:
                self.controller._notify_battle_sound('snd_rudebuster_hit', 1.0)
        # scr_oflash and scr_afterimage are still sprite/FX dependencies;
        # store the visual records without treating them as combat damage.
        self.bursts = [RudeBusterBurst((45 + i * 90) % 360,
                                      40 if self.bonus_anim else 25)
                       for i in range(8)]

    def step(self) -> None:
        if not self.alive:
            return
        self.image_alpha = min(1.0, self.image_alpha + 0.25)
        if self.t == 0:
            self._initial_step()
        elif not self.explode:
            from math import hypot
            self.bolt_timer += 1
            if self._press and self.bolt_timer >= 4 and self.chosen_bolt == 0 and not self.lockdamage:
                self.chosen_bolt = self.bolt_timer
                self.lockdamage = True
            toward = self._direction(self.x, self.y, self.cx, self.cy)
            self.direction = (self.direction + self._difference(toward, self.direction) / 4) % 360
            self.image_angle = self.direction
            if hypot(self.x - self.cx, self.y - self.cy) <= 40:
                self.final_bolt = self.bolt_timer
                self.visible = False
                self.explode = 1
                self.t = 1
        self._press = False
        if self.explode:
            if self.t == 1:
                self._impact()
            elif self.t >= 2:
                for i, burst in enumerate(self.bursts):
                    burst.step(i)
            if self.t >= 18:
                self.alive = False
        else:
            # Motion properties are applied by GameMaker after the Step event.
            from math import radians, sin, cos
            # scr_afterimage samples the pre-motion position; GameMaker
            # advances speed/direction after finishing the Step event.
            self.trails.append(RudeBusterTrail(self.x, self.y, self.image_angle,
                                              self.image_alpha - 0.2))
            self.maxaft += 1
            self.x += cos(radians(self.direction)) * self.speed
            self.y -= sin(radians(self.direction)) * self.speed
            self.speed = max(0.0, self.speed - self.friction)
        self.trails = [a for a in self.trails if a.step(bool(self.explode))]
        self.a += 1
        self.t += 1
