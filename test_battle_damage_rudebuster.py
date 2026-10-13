"""Regression tests for recovered scr_damage_enemy and obj_rudebuster_anim."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from battle import BattleController, PartySpawn
from battle_combat import BattleCombatController
from battle_effects import DamageWriterEvent, RudeBusterAnimation
from battle_monsters import MonsterHooks
from battle_spells import scr_spell
from battle_view import BattleCanvasView
from encounter_setup import setup_encounter
from test_battle_spell_effects import make
from test_battle_view import CanvasStub


class DamageEnemyTests(unittest.TestCase):
    def test_damage_writer_stacks_20_pixels_and_sets_type(self):
        c = make(party=(1, 2, 4))
        e = c.state.enemies[0]
        self.assertEqual(c.damage_enemy(0, 18, 1), 18)
        self.assertEqual(c.damage_enemy(0, 9, 2), 9)
        first, second = c.state.damage_writer_events
        self.assertIsInstance(first, DamageWriterEvent)
        self.assertEqual((first.x, first.y), (e.x, e.y + 20))
        self.assertEqual((second.x, second.y), (e.x, e.y))
        self.assertEqual((first.type, second.type), (1, 6))
        self.assertEqual([ev.damage for ev in c.state.damage_writer_events], [18, 9])
        self.assertEqual(c.state.hittarget[0], 2)
        self.assertEqual(e.hit_target, 2)
        self.assertEqual(e.hp, 173)

    def test_caster_five_uses_special_damage_writer_type(self):
        c = make(party=(1,))
        c.scr_damage_enemy(0, 7, 5)
        self.assertEqual(c.state.damage_writer_events[-1].type, 5)

    def test_positive_hit_reacts_and_callback_before_defeat(self):
        events = []
        def damage_hook(enemy, actor, damage):
            events.append(('damage', enemy.hp, enemy.state, enemy.active, actor.slot))
        hooks = MonsterHooks(on_damage=damage_hook,
                             event_user_11=lambda e:events.append(('defeat', e.hp)))
        c = make(party=(1, 2), monster_hooks={'*': hooks})
        e = c.state.enemies[0]
        e.hp = 8
        self.assertEqual(c.damage_enemy(0, 20, 1), 20)
        self.assertEqual(events, [('damage', -12, 0, True, 1), ('defeat', -12)])
        self.assertEqual((e.shakex, e.hurttimer, e.hurtamt, e.state), (9, 30, 20, 3))
        self.assertFalse(e.active)
        self.assertEqual(c.flags[51], 1)
        self.assertEqual(c.state.reward_gold, 35)
        self.assertEqual(c.state.hittarget[0], 1)
        self.assertIsNone(c.damage_enemy(0, 1, 1))
        self.assertEqual(len(c.state.damage_writer_events), 1)

    def test_callback_can_intercept_lethal_damage(self):
        def hold_at_one(enemy, actor, damage):
            enemy.hp = max(1, enemy.hp)
        c = make(party=(1,), monster_hooks={'*': MonsterHooks(on_damage=hold_at_one)})
        c.state.enemies[0].hp = 8
        c.damage_enemy(0, 20, 0)
        self.assertTrue(c.state.enemies[0].active)
        self.assertEqual(c.state.enemies[0].hp, 1)

    def test_zero_damage_dodge_if_dodgeable(self):
        c = make(party=(1,))
        e = c.state.enemies[0]
        e.candodge = 1
        e.hurttimer = 15
        e.dodgetimer = 9
        e.hurtamt = 13
        hp = e.hp
        self.assertEqual(c.damage_enemy(0, 0, 0), 0)
        self.assertEqual((e.state, e.dodgetimer, e.hurtamt), (4, 0, 0))
        self.assertEqual(e.hp, hp)
        self.assertEqual(c.state.hittarget[0], 1)

    def test_zero_damage_does_not_dodge_without_both_conditions(self):
        for timer, flag in ((16, 1), (15, 0)):
            with self.subTest(timer=timer, candodge=flag):
                c = make(party=(1,))
                e = c.state.enemies[0]
                e.state = 7
                e.hurttimer, e.candodge = timer, flag
                c.damage_enemy(0, 0, 0)
                self.assertEqual(e.state, 7)

    def test_negative_damage_preserved_from_gml(self):
        c = make(party=(1,))
        hp = c.state.enemies[0].hp
        self.assertEqual(c.damage_enemy(0, -5, 0), -5)
        self.assertEqual(c.state.enemies[0].hp, hp + 5)
        self.assertEqual(c.state.damage_writer_events[0].damage, -5)

    def test_unknown_hp_does_not_spawn_writer_or_defeat(self):
        c = make(party=(1,))
        c.state.enemies[0].hp = None
        self.assertIsNone(c.damage_enemy(0, 22, 0))
        self.assertEqual(c.state.damage_writer_events, [])
        self.assertTrue(c.state.enemies[0].active)

    def test_spell_one_applies_damage_then_sets_writer_delay_eight(self):
        c = make(party=(1,))
        c.state.chartarget[0] = 0
        r = scr_spell(c, 1, 0)
        self.assertEqual(r.direct_damage, 108)
        self.assertEqual(c.state.damage_writer_events[-1].delay, 8)
        self.assertEqual(c.state.damage_writer_events[-1].damage, 108)
        self.assertEqual(c.state.spell_animation_events[-1].object_name, 'obj_basicattack')


class RudeBusterAnimationTests(unittest.TestCase):
    def make_animation(self, *, red=False, callbacks=None):
        callback_events = []
        c = make(party=(1, 2), on_spell_animation=lambda s,r:callback_events.append(r),
                 on_hero_sound=lambda name, pitch, actor:callback_events.append(('sound',name, actor.character_id)))
        c.state.chartarget[1] = 0
        r = scr_spell(c, 5 if red else 4, 1)
        self.assertEqual(len(r.animations), 1)
        self.assertEqual(len(c.rudebuster_animations), 1)
        return c, c.rudebuster_animations[0], callback_events

    def test_create_hides_susie_and_prepares_source_defaults(self):
        c, a, events = self.make_animation()
        susie = c.state.actors[1]
        self.assertFalse(susie.visible)
        self.assertEqual(a.t, 0)
        self.assertEqual(a.image_index, 0)
        self.assertEqual(a.battlemode, 1)
        self.assertEqual((a.x, a.y), (susie.x, susie.y))
        self.assertTrue(a.alive)
        self.assertFalse(a.projectile_fired)
        self.assertEqual(events[0].object_name, 'obj_rudebuster_anim')

    def test_bolt_spawns_when_t_ten_not_before(self):
        c, anim, events = self.make_animation()
        c.update(10)
        self.assertEqual(anim.t, 10)
        self.assertFalse(anim.projectile_fired)
        c.update(1)
        self.assertTrue(anim.projectile_fired)
        self.assertEqual(anim.t, 11)
        self.assertEqual(anim.image_index, 5)
        bolt = c.state.spell_animation_events[-1]
        self.assertEqual(bolt.object_name, 'obj_rudebuster_bolt')
        self.assertEqual(bolt.damage, 8 * 5 + 15 * 11 - 4 * 3)
        self.assertEqual(bolt.target_slot, 0)
        self.assertEqual(dict(bolt.extra)['x'], anim.x + 40)
        self.assertEqual(dict(bolt.extra)['y'], anim.y + 30)
        self.assertEqual(events[-1], ('sound', 'snd_rudebuster_swing', 2))
        self.assertEqual(c.state.enemies[0].hp, 200)
        self.assertEqual(c.state.damage_writer_events, [])
        c.update(5)
        self.assertEqual(sum(e.object_name=='obj_rudebuster_bolt' for e in
                             c.state.spell_animation_events), 1)

    def test_red_variant_passes_red_to_projectile_without_damage(self):
        c, anim, _ = self.make_animation(red=True)
        c.update(11)
        bolt = c.state.spell_animation_events[-1]
        self.assertEqual(dict(bolt.extra)['red'], 1)
        self.assertEqual(bolt.damage, 8 * 6 + 15 * 13 - 4 * 6)
        self.assertEqual(c.state.enemies[0].hp, 200)

    def test_parent_restores_susie_at_t_twenty_eight(self):
        c, anim, _ = self.make_animation()
        c.update(28)
        self.assertEqual(anim.t, 28)
        self.assertFalse(c.state.actors[1].visible)
        c.update(1)
        self.assertTrue(c.state.actors[1].visible)
        self.assertFalse(anim.alive)
        self.assertEqual(c.rudebuster_animations, [])

    def test_dead_target_prevents_bolt_spawn_not_parent_cleanup(self):
        c, anim, _ = self.make_animation()
        c.defeat_enemy(0)
        c.update(11)
        self.assertFalse(anim.projectile_fired)
        self.assertFalse(any(q.object_name == 'obj_rudebuster_bolt'
                             for q in c.state.spell_animation_events))
        c.update(18)
        self.assertTrue(c.state.actors[1].visible)

    def test_parent_survives_after_writer_phase_completes(self):
        c, anim, _ = self.make_animation()
        c.state.resolution_stage = 'spell_phase'
        c.update(7)
        self.assertTrue(anim.alive)
        self.assertFalse(c.state.actors[1].visible)

    def test_blue_target_yellow_intercepts(self):
        c, anim, _ = self.make_animation()
        blue = c.state.enemies[0]
        yellow = c.state.enemies[1]
        blue.object_name = 'obj_blue_enemy'
        yellow.object_name = 'obj_yellow_enemy'
        c.state.chartarget[1] = blue.slot
        old_x = blue.x
        c.update(11)
        bolt = c.state.spell_animation_events[-1]
        self.assertEqual(bolt.target_slot, yellow.slot)
        self.assertEqual(c.state.chartarget[1], yellow.slot)
        self.assertEqual(yellow.x, blue.x-60)
        self.assertEqual(yellow.y, blue.y)
        self.assertEqual((yellow.blockcon,yellow.blocktimer,yellow.hurtsprite),
                         (1,0,'spr_yellow_block'))
        self.assertEqual(dict(bolt.extra)['instance_target'], 171)
        self.assertEqual(c.state.monster_slots[yellow.slot].monsterx, old_x - 60)

    def test_yellow_blue_other_target_sets_yellowbluecon(self):
        c, anim, _ = self.make_animation()
        c.state.enemies[0].object_name='obj_yellow_enemy'
        c.state.enemies[1].object_name='obj_blue_enemy'
        c.state.chartarget[1] = 0
        c.update(11)
        self.assertEqual(dict(c.state.spell_animation_events[-1].extra)['yellowbluecon'], 1)

    def test_no_susie_actor_creates_non_battle_variant(self):
        c = make(party=(1,))
        c.state.chartarget[0] = 0
        # This is the object-level Create case (not a legal Susie spell cast).
        from battle_spells import SpellAnimationRequest
        c._emit_spell_animation(SpellAnimationRequest('obj_rudebuster_anim', 0, 0, 10))
        anim = c.rudebuster_animations[0]
        self.assertEqual(anim.battlemode, 0)
        self.assertIsNone(anim.susie_actor_slot)
        c.update(29)
        self.assertFalse(anim.alive)

    def test_view_hides_susie_and_marks_parent_without_advancing_it(self):
        canvas = CanvasStub()
        game = SimpleNamespace(canvas=canvas, scale=2,
                               ui_to_screen=lambda x,y:(x*2,y*2))
        view = BattleCanvasView(game)
        layout = setup_encounter(1)
        view.start(layout)
        battle = BattleController()
        entry = battle.start_battle(1, 0, layout.enemy_slots, {}, party_members=[
            PartySpawn(1,0,0,80,140), PartySpawn(2,0,0,80,140)])
        battle.update(24)
        c, anim, _ = self.make_animation()
        view.render(entry, c)
        all_text=[r[2]['text'] for r in canvas.actions if r[0]=='text']
        self.assertIn('RUDE BUSTER', all_text)
        self.assertFalse(any(t=='Susie' for t in all_text))
        self.assertEqual(anim.t, 0)


if __name__ == '__main__':
    unittest.main()

class SameFrameSpawnTests(unittest.TestCase):
    def test_new_parent_does_not_receive_step_on_spawn_frame(self):
        c = make(party=(1, 2))
        c.state.charspecial[1] = 4
        c.state.chartarget[1] = 0
        susie = c.state.actors[1]
        anim = susie.hero_animation
        # Simulates obj_spellphase's cast: sets hero to 2 and starts timer.
        susie.state = 2
        anim.itemed = 0
        c.update(16)
        self.assertEqual(len(c.rudebuster_animations), 1)
        parent = c.rudebuster_animations[0]
        self.assertEqual(parent.t, 0)
        self.assertFalse(susie.visible)
        c.update(11)
        self.assertTrue(parent.projectile_fired)
        self.assertEqual(c.state.enemies[0].hp, 200)
