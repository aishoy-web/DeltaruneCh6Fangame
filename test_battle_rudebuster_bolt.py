"""Source-driven tests for obj_rudebuster_bolt Create / Step / Draw."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from battle import BattleController, PartySpawn
from battle_effects import RudeBusterBolt
from battle_spells import SpellAnimationRequest, scr_spell
from battle_view import BattleCanvasView
from encounter_setup import setup_encounter
from test_battle_spell_effects import make
from test_battle_view import CanvasStub


class BoltTestCase(unittest.TestCase):
    def bolt(self, *, damage=20, red=False, party=(1, 2), **kw):
        c = make(party=party, **kw)
        enemy = c.state.enemies[0]
        c._emit_spell_animation(SpellAnimationRequest(
            'obj_rudebuster_bolt', 1 if 2 in party else 0, enemy.slot,
            damage, extra=(('x', enemy.x - 12), ('y', enemy.y),
                           ('red', int(red)), ('battlemode', 1))))
        return c, c.rudebuster_bolts[0]

    def impact(self, bolt, *, final=10, chosen=0):
        """Place an already-flying projectile inside its 40px contact area."""
        bolt.t = 1
        bolt.bolt_timer = final - 1
        bolt.chosen_bolt = chosen
        bolt.cx = bolt.x
        bolt.cy = bolt.y
        bolt.step()


class RudeBusterBoltCreateTests(BoltTestCase):
    def test_create_defaults_and_request_fields(self):
        c, b = self.bolt(red=True)
        self.assertEqual((b.t, b.damage, b.red, b.star), (0, 20, 1, 0))
        self.assertEqual((b.image_alpha, b.image_speed), (0, 1))
        self.assertEqual((b.image_xscale, b.image_yscale), (2, 2))
        self.assertTrue(b.alive)
        self.assertFalse(b.lockdamage)
        self.assertEqual((b.bolt_timer, b.chosen_bolt, b.final_bolt), (0, 0, 0))
        self.assertEqual(c.state.enemies[0].hp, 200)

    def test_initial_frame_captures_target_position_and_direction_offset(self):
        c, b = self.bolt()
        target = c.state.enemies[0]
        b.step()
        self.assertEqual((b.cx, b.cy), (target.x, target.y))
        self.assertAlmostEqual(b.image_angle, 340, delta=0.01)
        self.assertAlmostEqual(b.speed, 25.5)
        self.assertAlmostEqual(b.image_alpha, 0.25)
        self.assertEqual(b.t, 1)
        self.assertEqual(len(b.trails), 1)

    def test_red_variant_sprite_and_scale_start_on_first_step(self):
        _, b = self.bolt(red=True)
        b.step()
        self.assertEqual(b.image_sprite, 'spr_rudebuster_beam_red')
        self.assertEqual((b.image_xscale, b.image_yscale), (2.5, 2.5))

    def test_source_direction_uses_gamemaker_up_is_positive(self):
        self.assertEqual(RudeBusterBolt._direction(0, 0, 0, -20), 90)
        self.assertEqual(RudeBusterBolt._direction(0, 0, 20, 0), 0)
        self.assertEqual(RudeBusterBolt._difference(10, 350), 20)
        self.assertEqual(RudeBusterBolt._difference(350, 10), -20)

    def test_button_ignored_until_bolt_timer_reaches_four(self):
        _, b = self.bolt()
        b.t = 1
        b.cx, b.cy = b.x + 1000, b.y
        b.bolt_timer = 2
        b.button('z')
        b.step()
        self.assertEqual((b.chosen_bolt, b.lockdamage), (0, False))
        b.button('z')
        b.step()
        self.assertEqual((b.chosen_bolt, b.lockdamage), (4, True))
        b.button('z')
        b.step()
        self.assertEqual(b.chosen_bolt, 4)

    def test_non_button1_does_not_lock(self):
        _, b = self.bolt()
        b.t = 1
        b.cx, b.cy = b.x + 999, b.y
        b.bolt_timer = 5
        b.button('x')
        b.step()
        self.assertEqual(b.chosen_bolt, 0)


class RudeBusterImpactTests(BoltTestCase):
    def test_contact_applies_damage_only_once(self):
        c, b = self.bolt()
        self.assertEqual(c.state.enemies[0].hp, 200)
        b.step()  # t=0 initialization and motion (not damage)
        self.assertEqual(c.state.enemies[0].hp, 200)
        b.step()  # now close to enemy
        self.assertEqual(c.state.enemies[0].hp, 180)
        self.assertEqual(b.impact_damage, 20)
        self.assertEqual(len(c.state.damage_writer_events), 1)
        self.assertEqual(c.state.hittarget[0], 1)
        for _ in range(10):
            b.step()
        self.assertEqual(c.state.enemies[0].hp, 180)
        self.assertEqual(len(c.state.damage_writer_events), 1)

    def test_exact_timing_bonus_table(self):
        bonuses = {0: 30, 1: 28, 2: 22, 3: 20, 4: 13, 5: 11, 6: 10, 7: 0}
        for offset, bonus in bonuses.items():
            with self.subTest(offset=offset):
                c, b = self.bolt()
                self.impact(b, final=11, chosen=11-offset)
                self.assertEqual(b.impact_damage, 20+bonus)
                self.assertEqual(c.state.enemies[0].hp, 180-bonus)
                self.assertEqual(b.bonus_anim, int(offset <= 2))

    def test_early_negative_offset_gets_no_bonus_but_special_fx(self):
        c, b = self.bolt()
        self.impact(b, final=10, chosen=11)
        self.assertEqual(b.impact_damage, 20)
        self.assertEqual(b.bonus_anim, 1)  # abs(chosen-final) <= 2
        self.assertEqual(c.state.enemies[0].hp, 180)

    def test_no_press_means_no_bonus(self):
        c, b = self.bolt()
        self.impact(b, chosen=0)
        self.assertEqual(b.impact_damage, 20)
        self.assertFalse(b.bonus_anim)

    def test_red_plus_ninety_after_timing_bonus(self):
        c, b = self.bolt(red=True)
        self.impact(b, final=10, chosen=10)
        self.assertEqual(b.impact_damage, 140)
        self.assertEqual(c.state.enemies[0].hp, 60)

    def test_trashy_damage_reduction_and_hp_restore(self):
        c, b = self.bolt(damage=70, red=True)
        enemy = c.state.enemies[0]
        enemy.object_name = 'obj_trashy_trio'
        self.impact(b, final=10, chosen=10)
        # ceil((70 + 30)*.1) + 90 = 100; HP restores after hit.
        self.assertEqual(b.impact_damage, 100)
        self.assertEqual(enemy.hp, 200)
        self.assertEqual(enemy.back, 30)
        self.assertEqual(c.state.damage_writer_events[-1].damage, 100)

    def test_pink_enemy_zeroes_damage_writers_without_cancelling_hp(self):
        c, b = self.bolt()
        c.state.enemies[1].object_name = 'obj_pink_enemy'
        c.damage_enemy(1, 4, 1)
        self.impact(b)
        self.assertEqual(c.state.enemies[0].hp, 180)
        self.assertEqual([w.damage for w in c.state.damage_writer_events], [0, 0])

    def test_damage_callback_receives_effective_bonus_damage(self):
        from battle_monsters import MonsterHooks
        seen = []
        c, b = self.bolt(red=True, monster_hooks={'*': MonsterHooks(
            on_damage=lambda enemy, actor, amount: seen.append((enemy.hp, amount, actor.slot))
        )})
        self.impact(b, final=12, chosen=11)
        self.assertEqual(seen, [(200 - 20 - 28 - 90, 138, 1)])

    def test_regular_bolt_extra_damage_overruns_hp_and_collects_rewards(self):
        c, b = self.bolt(damage=170)
        self.impact(b, final=9, chosen=9)
        self.assertEqual(b.impact_damage, 200)
        self.assertEqual(c.state.enemies[0].hp, 0)
        self.assertFalse(c.state.enemies[0].active)
        self.assertEqual(c.state.reward_gold, 35)

    def test_lethal_hit_invokes_defeat_and_rewards_once(self):
        c, b = self.bolt(damage=250)
        self.impact(b)
        self.assertFalse(c.state.enemies[0].active)
        self.assertEqual(c.flags[51], 1)
        self.assertEqual(c.state.reward_gold, 35)
        b.step()
        self.assertEqual(c.state.reward_gold, 35)

    def test_missing_enemy_hp_does_not_invent_damage(self):
        c, b = self.bolt(damage=40)
        c.state.enemies[0].hp = None
        self.impact(b)
        self.assertIsNone(c.state.enemies[0].hp)
        self.assertEqual(c.state.damage_writer_events, [])

    def test_missing_target_does_not_damage_another_slot(self):
        c, b = self.bolt()
        c.defeat_enemy(0)
        old_hp = c.state.enemies[1].hp
        self.impact(b)
        self.assertEqual(c.state.enemies[1].hp, old_hp)
        self.assertEqual(len(c.state.damage_writer_events), 0)

    def test_hit_resets_previous_hit_stack_before_damage_writer(self):
        c, b = self.bolt()
        c.state.hittarget[0] = 3
        self.impact(b)
        self.assertEqual(c.state.damage_writer_events[-1].y,
                         c.state.enemies[0].y + 20)
        self.assertEqual(c.state.hittarget[0], 1)

    def test_bursts_live_until_t_eighteen_then_die(self):
        c, b = self.bolt()
        self.impact(b)
        self.assertEqual(len(b.bursts), 8)
        self.assertFalse(b.visible)
        self.assertEqual(b.t, 2)
        for _ in range(17):
            b.step()
        self.assertFalse(b.alive)
        self.assertEqual(len(c.state.damage_writer_events), 1)

    def test_impact_plays_recovered_sounds(self):
        sounds = []
        c, b = self.bolt(on_hero_sound=lambda name,pitch,actor:sounds.append(name))
        self.impact(b, final=11, chosen=11)
        self.assertIn('snd_scytheburst', sounds)
        self.assertIn('snd_rudebuster_hit', sounds)


class RudeBusterIntegrationTests(BoltTestCase):
    def test_spawned_bolt_is_stepped_on_next_frame_not_parent_spawn(self):
        c = make(party=(1, 2))
        c.state.chartarget[1] = 0
        scr_spell(c, 4, 1)
        c.update(11)
        self.assertEqual(len(c.rudebuster_bolts), 1)
        b = c.rudebuster_bolts[0]
        self.assertEqual(b.t, 0)
        self.assertEqual(c.state.enemies[0].hp, 200)
        c.update(1)
        self.assertEqual(b.t, 1)
        self.assertEqual(c.state.enemies[0].hp, 200)
        c.update(40)
        self.assertEqual(c.state.enemies[0].hp, 7)
        self.assertFalse(c.rudebuster_bolts)

    def test_controller_routes_z_to_bolt_even_during_spell_phase(self):
        c, b = self.bolt()
        c.state.phase = 'awaiting_resolution'
        c.state.resolution_stage = 'spell_phase'
        b.t = 1
        b.bolt_timer = 3
        b.cx, b.cy = b.x+1000, b.y
        c.handle_key('z')
        c.update(1)
        self.assertEqual(b.chosen_bolt, 4)
        c.handle_key('z')
        c.update(1)
        self.assertEqual(b.chosen_bolt, 4)

    def test_view_is_read_only_and_draws_beam_trail_and_burst(self):
        canvas = CanvasStub()
        game = SimpleNamespace(canvas=canvas, scale=2,
                               ui_to_screen=lambda x, y: (x*2, y*2))
        view = BattleCanvasView(game)
        layout = setup_encounter(1)
        view.start(layout)
        battle = BattleController()
        entry = battle.start_battle(1, 0, layout.enemy_slots, {},
                                    party_members=[PartySpawn(1,0,0,80,140)])
        battle.update(24)
        c, b = self.bolt()
        c.update(1)
        t = b.t
        view.render(entry, c)
        self.assertTrue(any(action[0] == 'line' for action in canvas.actions))
        self.assertTrue(any(action[0] == 'oval' for action in canvas.actions))
        self.assertEqual(b.t, t)
        self.impact(b)
        view.render(entry, c)
        self.assertEqual(b.t, 2)
        self.assertEqual(len(b.bursts), 8)


if __name__ == '__main__':
    unittest.main()
