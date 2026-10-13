"""Headless tests for the supplied obj_attackpress and obj_spellphase events."""
import random
import unittest
from battle_combat import BattleCombatController, CombatOption, QueuedAction
from battle_phases import AttackPressPhase, SpellPhase
from encounter_setup import setup_encounter


def make(party=(1, 2, 3), flags=None, auto=None, **kwargs):
    return BattleCombatController(
        setup_encounter(203, party_ids=party), party,
        flags if flags is not None else {},
        party_auto=auto or {}, **kwargs)


class AttackCreateTests(unittest.TestCase):
    def test_single_attacker_allocates_bolt_and_copies_target(self):
        c = make(party=(1,))
        s = c.state
        s.charaction = [1, 0, 0]
        s.chartarget = [2, 1, 0]
        p = AttackPressPhase(s, c.flags, c.party_auto, rng=random.Random(1))
        self.assertEqual(p.havechar, [1,0,0])
        self.assertEqual(p.bolttotal, 1)
        self.assertEqual(p.bolts[0].party_slot, 0)
        self.assertEqual(p.bolts[0].frame, 29)
        self.assertEqual(s.hittarget, [2,1,0])
        self.assertEqual(p.timermax, 50)
        self.assertTrue(p.active)

    def test_three_attacks_schedule_one_bolt_each(self):
        c = make()
        s = c.state
        s.charaction[:] = [1,1,1]
        p = AttackPressPhase(s, c.flags, {}, rng=random.Random(47))
        self.assertEqual(sorted(b.party_slot for b in p.bolts), [0,1,2])
        self.assertEqual(len(set(b.party_slot for b in p.bolts)), 3)
        self.assertEqual(p.bolts[0].frame, 29)
        self.assertTrue(all(p.bolts[i].frame < p.bolts[i+1].frame for i in range(2)) or
                        all(p.bolts[i].frame <= p.bolts[i+1].frame for i in range(2)))

    def test_no_attacker_uses_three_frame_timer(self):
        c = make(party=(1,))
        p = AttackPressPhase(c.state, c.flags, {}, rng=random.Random(5))
        self.assertEqual(p.timermax, 3)
        for _ in range(4):
            p.advance()
        self.assertTrue(p.finished)

    def test_spell_maxdelay_does_not_disable_fastmode(self):
        c = make()
        c.state.charaction[:] = [2, 4, 1]
        p = AttackPressPhase(c.state, c.flags, {})
        self.assertEqual(p.maxdelay, 55)
        p.advance()
        self.assertTrue(p.active)

    def test_one_button_records_input_but_does_not_guess_damage(self):
        calls = []
        c = make(party=(1,), on_bolt_check=lambda phase, slot: calls.append(slot))
        c.state.charaction[0] = 1
        p = AttackPressPhase(c.state, c.flags, {}, on_bolt_check=c.on_bolt_check)
        self.assertTrue(p.button('z'))
        self.assertEqual(calls, [None])
        self.assertEqual(p.points[0], 0)
        self.assertTrue(p.bolts[0].alive)
        self.assertFalse(p.button('x'))

    def test_three_button_input_is_limited_to_selected_attacker(self):
        c = make(flags={13:1})
        c.state.charaction[:] = [1, 0, 1]
        p = AttackPressPhase(c.state, c.flags, {})
        self.assertTrue(p.button('z'))
        self.assertFalse(p.button('x'))
        self.assertTrue(p.button('c'))
        self.assertEqual(p.button_events, [(0,0),(0,2)])

    def test_callback_can_supply_score_and_other11_forwards_to_hero(self):
        calls = []
        c = make(party=(1,), on_hero_attack=lambda state, actor, slot: calls.append((slot, actor.points, actor.state)))
        c.state.charaction[0] = 1
        p = AttackPressPhase(c.state, c.flags, {}, rng=random.Random(0),
                             on_attack_trigger=c.on_hero_attack)
        p.set_bolt_result(0, 172)
        p.advance()
        self.assertEqual(calls, [(0,172,1)])
        self.assertEqual(c.state.actors[0].points, 172)
        self.assertEqual(c.state.actors[0].attacktimer, 0)

    def test_unchecked_bolt_triggers_attack_with_zero_points(self):
        c = make(party=(1,))
        c.state.charaction[0] = 1
        p = AttackPressPhase(c.state, c.flags, {})
        for _ in range(55):
            p.advance()
        self.assertEqual(p.attacked[0], 1)
        self.assertEqual(c.state.actors[0].points, 0)

    def test_auto_susie_uses_160_point_source_value(self):
        c = make(party=(1,2), auto={2:1}, party_stats={2:{'hp':20,'max_hp':30}})
        p = AttackPressPhase(c.state, c.flags, c.party_auto)
        self.assertTrue(p.haveauto)
        for _ in range(60):
            p.advance()
            if p.autoed:
                break
        self.assertTrue(p.autoed)
        susie = next(a for a in c.state.actors if a.character_id == 2)
        self.assertEqual(susie.points, 160)
        self.assertTrue(susie.is_auto_susie)


class ControllerPhaseTests(unittest.TestCase):
    def test_attack_phase_creates_and_advances_real_attack_object(self):
        c = make(party=(1,))
        s = c.state
        s.charaction[0] = 1
        c.attack_phase()
        self.assertIsNotNone(c.attack_press)
        self.assertEqual(s.resolution_stage, 'attack_press')
        c.update(2)
        self.assertEqual(c.attack_press.boltx, 2)
        self.assertEqual(c.attack_press.maxdelaytimer, 2)

    def test_attack_phase_finishes_with_enemy_turn_pending_not_ai(self):
        c = make(party=(1,))
        c.attack_phase()
        c.update(4)
        self.assertEqual(c.state.myfight, -1)
        self.assertEqual(c.state.mnfight, 1)
        self.assertEqual(c.state.resolution_stage, 'enemy_turn_pending')
        self.assertEqual(c.state.phase, 'awaiting_resolution')

    def test_attack_finishes_on_victory_if_monsters_removed_during_timing(self):
        c = make(party=(1,))
        c.attack_phase()
        for enemy in c.state.enemies:
            c.deactivate_enemy(enemy.slot)
        c.update(60)
        self.assertIn(c.state.phase, ('victory','awaiting_wincombat'))

    def test_attack_key_events_are_forwarded_by_controller(self):
        seen = []
        c = make(party=(1,), on_bolt_check=lambda phase, slot: seen.append(slot))
        c.state.charaction[0] = 1
        c.attack_phase()
        c.handle_key('z')
        self.assertEqual(seen,[None])

    def test_spell_phase_triggers_alarm_after_five_frames(self):
        c = make(party=(1,2))
        c.state.charaction[:] = [2,4,0]
        c.attack_phase()
        p = c.spell_phase
        self.assertEqual((p.alarm0,p.active), (5,0))
        c.update(4)
        self.assertEqual(p.spelltotal, 0)
        c.update(1)
        self.assertEqual(p.spelltotal, 2)
        self.assertEqual(p.cast_history, [(0,'spell')])
        self.assertEqual(c.state.actors[0].state, 2)
        self.assertEqual(c.state.spelldelay, 90)

    def test_sequential_spell_then_item_then_attackpress(self):
        c = make(party=(1,2))
        c.state.charaction[:] = [2,4,0]
        c.attack_phase()
        p = c.spell_phase
        # scr_spell now restores global.spelldelay=10 when an effect fires,
        # replacing the former callback-only 90-frame placeholder.
        c.update(25)
        self.assertEqual(p.cast_history, [(0,'spell'),(1,'item')])
        self.assertEqual(c.state.actors[1].state, 4)
        c.update(13)
        self.assertEqual(c.state.resolution_stage, 'attack_press')
        self.assertEqual(c.state.myfight, 1)
        self.assertIsNotNone(c.attack_press)

    def test_writer_blocks_spell_progress_until_explicitly_dismissed(self):
        c = make(party=(1,), on_spell_cast=lambda state, slot, kind: True)
        c.state.charaction[0] = 2
        c.attack_phase()
        c.update(100)
        self.assertEqual(c.state.resolution_stage, 'spell_phase')
        self.assertTrue(c.spell_phase.writer_alive)
        c.dismiss_spell_text()
        c.update(1)
        self.assertEqual(c.state.resolution_stage, 'attack_press')

    def test_queued_spell_without_numeric_action_still_casts(self):
        c = make(party=(1,))
        c.register_spells(0,[CombatOption('Example Spell', tp_cost=0, target=0)])
        c.state.queued[0] = QueuedAction(0, 'spell', option=CombatOption('Example Spell'))
        c.attack_phase()
        p = c.spell_phase
        self.assertIsNotNone(p)
        c.update(5)
        self.assertEqual(p.cast_history, [(0,'spell')])
        self.assertEqual(c.state.charaction, [0,0,0])

    def test_queued_act_without_numeric_spell_does_not_hang_phase(self):
        c = make(party=(1,))
        c.state.queued[0] = None
        c.state.myfight = 3
        c.state.charaction = [0,0,0]
        c.state.phase = 'awaiting_resolution'
        # Adapter entry for an unresolved action lacking scr_actselect codes.
        c.state.queued[0] = QueuedAction(0, 'act',0)
        c.attack_phase()
        self.assertEqual(c.state.resolution_stage, 'spell_phase')
        c.update(95)
        self.assertEqual(c.state.resolution_stage, 'attack_press')


if __name__ == '__main__':
    unittest.main()
