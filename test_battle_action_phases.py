"""Regression tests for scr_attackphase, scr_nextact, scr_act_simul.

Only control flow and flags are tested: the source here does not contain
obj_attackpress, obj_spellphase, scr_actselect, or the individual monster ACTs.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

from battle_combat import BattleCombatController, CombatOption
from encounter_setup import setup_encounter


def make(party=(1,), encounter=1, *, camera_origin=(0, 0), **kwargs):
    layout = setup_encounter(encounter, party, camera_origin=camera_origin)
    return BattleCombatController(layout, party, {}, **kwargs)


def select_act(c, *, enemy_slot=0, option_slot=0):
    """Drive actual menu input to select a registered ACT."""
    s = c.state
    c.handle_key("Right")
    c.handle_key("z")
    if s.bmenuno == 11:
        s.bmenucoord[11][s.charturn] = enemy_slot
        c.handle_key("z")
    else:
        raise AssertionError("This test requires a Kris ACT menu")
    s.bmenucoord[9][s.charturn] = option_slot
    c.handle_key("z")


class AttackPhaseTests(unittest.TestCase):
    def test_fight_spawns_attackpress_only_and_resets_hit_targets(self):
        events = []
        c = make(camera_origin=(200, 300),
                 on_attack_press_start=lambda s: events.append(("press", s.myfight)),
                 on_spell_phase_start=lambda s: events.append(("spell", s.myfight)),
                 on_attack_phase=lambda s: events.append(("notify", s.fightphase)))
        s = c.state
        s.charaction[0] = 1
        s.hittarget[:] = [2, 3, 4]
        for e in s.enemies:
            e.hit_target = 7
        c.attack_phase()
        self.assertEqual(events, [("press", 1), ("notify", 1)])
        self.assertEqual((s.myfight, s.charturn, s.fightphase), (1, 3, 1))
        self.assertEqual(s.resolution_stage, "attack_press")
        self.assertEqual(s.attack_press_position, (202, 665))
        self.assertIsNone(s.spell_phase_position)
        self.assertEqual(s.hittarget, [0] * 3)
        self.assertTrue(all(e.hit_target == 0 for e in s.enemies))
        self.assertTrue(all(e.active and e.hp is None for e in s.enemies))

    def test_any_character_action_2_or_4_uses_spellphase(self):
        for index, action in ((0, 2), (1, 4), (2, 2)):
            with self.subTest(slot=index, action=action):
                events = []
                c = make(on_spell_phase_start=lambda s: events.append('spell'))
                c.state.charaction[index] = action
                c.attack_phase()
                self.assertEqual(events, ['spell'])
                self.assertEqual((c.state.myfight, c.state.fightphase), (4, 0))
                self.assertEqual(c.state.resolution_stage, 'spell_phase')
                self.assertEqual(c.state.spell_phase_position, (0, 0))
                self.assertIsNone(c.state.attack_press_position)

    def test_queued_registered_item_spell_or_act_prefer_spellphase(self):
        for kind in ('act', 'spell', 'item'):
            with self.subTest(kind=kind):
                c = make()
                # Do not invent charaction[]'s numeric code from the
                # unrecovered scr_*consumeb / scr_actselect scripts.
                from battle_combat import QueuedAction
                c.state.queued[0] = QueuedAction(0, kind)
                c.attack_phase()
                self.assertEqual(c.state.resolution_stage, 'spell_phase')
                self.assertEqual(c.state.charaction, [0, 0, 0])

    def test_myfight_four_forces_attackpress_even_with_queued_spell(self):
        from battle_combat import QueuedAction
        c = make()
        c.state.queued[0] = QueuedAction(0, 'spell')
        c.state.myfight = 4
        c.attack_phase()
        self.assertEqual(c.state.resolution_stage, 'attack_press')

    def test_previous_myfight_four_overrides_spellphase(self):
        c = make()
        s = c.state
        s.charaction[0] = 4
        s.myfight = 4
        c.attack_phase()
        self.assertEqual((s.fightphase, s.myfight), (1, 1))
        self.assertEqual(s.resolution_stage, 'attack_press')

    def test_no_monsters_calls_wincombat_instead_of_spawning_phase(self):
        events = []
        c = make(on_attack_press_start=lambda s: events.append('attack'))
        for e in c.state.enemies:
            c.deactivate_enemy(e.slot)
        c.attack_phase()
        self.assertEqual(c.state.phase, 'victory')
        self.assertEqual(events, [])

    def test_endturn_routes_into_real_attackphase_and_notification_once(self):
        events = []
        c = make(on_attack_press_start=lambda s: events.append('press'),
                 on_attack_phase=lambda s: events.append('attackphase'),
                 on_endturn=lambda s: events.append('endturn'))
        c.end_turn()
        c.end_turn()
        self.assertEqual(events, ['press', 'attackphase', 'endturn'])
        self.assertEqual((c.state.myfight, c.state.phase), (1, 'awaiting_resolution'))


class SingleACTTests(unittest.TestCase):
    def test_kris_registered_act_waits_not_immediately_skipped(self):
        events = []
        c = make(party=(1, 2),
                 on_act_started=lambda s, enemy, slot: events.append((slot, enemy.slot)))
        c.register_acts(1, 1, [CombatOption('Check')])
        s = c.state
        select_act(c, enemy_slot=1)
        self.assertEqual(s.charturn, 1)
        self.assertEqual((s.acting_flags[0], s.actingsingle[0], s.actingtarget[0]), (1, 1, 1))
        self.assertEqual(s.queued[0].target_slot, 1)
        c.handle_key('Left')  # Susie chooses DEFEND
        c.handle_key('z')
        self.assertEqual(s.resolution_stage, 'act')
        self.assertEqual(s.enemies[1].actcon, 1)
        self.assertEqual(events, [(0, 1)])
        c.next_act()  # Enemy finishes Kris's event
        self.assertEqual(s.acting_flags, [0, 0, 0])
        self.assertEqual(s.actingsingle[0], 0)
        self.assertEqual(s.enemies[1].actcon, 0)
        self.assertEqual(s.resolution_stage, 'spell_phase')

    def test_sequential_susie_then_ralsei_then_attackpress(self):
        events = []
        c = make(party=(1, 2, 3),
                 on_act_started=lambda s,e,slot: events.append((slot,e.slot)),
                 on_next_act=lambda s: events.append(('next',s.currentactingchar)))
        s = c.state
        s.actingsingle[1] = s.actingsingle[2] = 1
        s.actingtarget[1], s.actingtarget[2] = 0, 1
        c.end_turn()
        self.assertEqual(s.currentactingchar, 1)
        self.assertEqual(s.resolution_stage, 'next_act')
        self.assertEqual(s.enemies[0].actconsus, 1)
        self.assertEqual(events, [(1,0),('next',1)])
        c.next_act()
        self.assertEqual((s.enemies[0].actconsus, s.enemies[1].actconral), (0,1))
        self.assertEqual(s.currentactingchar, 2)
        c.next_act()
        self.assertEqual(s.enemies[1].actconral, 0)
        self.assertEqual(s.currentactingchar, 0)
        self.assertEqual(s.resolution_stage, 'attack_press')
        self.assertEqual(events, [(1,0),('next',1),(2,1),('next',2),('next',0)])

    def test_noelle_in_second_party_slot_gets_noelle_flag(self):
        c = make(party=(1, 4))
        s = c.state
        s.actingsingle[1] = 1
        c.end_turn()
        self.assertEqual(s.enemies[0].actconnoe, 1)
        self.assertEqual(s.currentactingchar, 1)

    def test_nextact_missing_target_does_not_invent_enemy_or_damage(self):
        c = make(party=(1,2))
        s = c.state
        c.deactivate_enemy(1)
        s.actingsingle[1] = 1
        s.actingtarget[1] = 1
        c.end_turn()
        self.assertEqual(s.actingsingle[1], 0)
        self.assertEqual(s.resolution_stage, 'attack_press')
        self.assertFalse(s.enemies[1].active)

    def test_undo_kris_act_clears_act_selection_and_flags(self):
        c = make(party=(1, 2))
        c.register_acts(0, 1, [CombatOption('Check')])
        select_act(c)
        c.handle_key('x')
        s = c.state
        self.assertEqual(s.charturn, 0)
        self.assertEqual(s.acting_flags[0], 0)
        self.assertEqual(s.actingsingle[0], 0)
        self.assertEqual(s.actingsimul[0], 0)
        self.assertEqual(s.actingtarget[0], 0)
        self.assertIsNone(s.queued[0])


class SimultaneousACTTests(unittest.TestCase):
    def test_kris_susie_ralsei_simultaneous_order_and_target_flags(self):
        started = []
        c = make(party=(1,2,3), on_act_started=lambda s,e,slot: started.append((slot,e.slot)))
        s = c.state
        for cid, target in ((1,0),(2,1),(3,0)):
            c.register_acts(target, cid, [CombatOption('Combo', simultaneous=True)])
        for slot, target in enumerate((0,1,0)):
            s.actingsingle[slot] = 1
            s.actingsimul[slot] = 1
            s.actingtarget[slot] = target
        s.acting_flags[0] = 1
        c.end_turn()
        self.assertEqual(s.resolution_stage, 'act_simul')
        self.assertEqual(s.simul_orders, {1:0, 2:1, 3:2})
        self.assertEqual(s.simul_total, 3)
        self.assertEqual(s.actingsingle, [0,0,0])
        self.assertEqual(s.enemies[0].actcon, 0)
        self.assertEqual(s.enemies[1].actconsus, 1)
        self.assertEqual(s.enemies[0].actconral, 1)
        self.assertEqual(s.enemies[1].simulorderkri, 0)
        self.assertEqual(s.enemies[0].simulordersus, 1)
        self.assertEqual(s.enemies[0].simulorderral, 2)
        self.assertEqual([e.simultotal for e in s.enemies], [3,3])
        self.assertEqual(started, [(0,0),(1,1),(2,0)])

    def test_non_simultaneous_act_remains_pending_for_next_act(self):
        c = make(party=(1,2,3))
        s = c.state
        c.register_acts(0, 1, [CombatOption('Combo', simultaneous=True)])
        c.register_acts(0, 2, [CombatOption('Talk')])
        c.register_acts(0, 3, [CombatOption('Combo', simultaneous=True)])
        s.actingsingle[:] = [1,1,1]
        s.actingsimul[:] = [1,0,1]
        s.acting_flags[0] = 1
        c.end_turn()
        self.assertEqual(s.actingsingle, [0,1,0])
        self.assertEqual(s.simul_orders, {1:0,3:1})
        c.next_act()
        self.assertEqual(s.currentactingchar, 1)
        self.assertEqual(s.enemies[0].actconsus, 1)

    def test_unregistered_simultaneous_does_not_assume_effect_or_clear_flag(self):
        c = make(party=(1,4))
        s = c.state
        s.actingsingle[1] = s.actingsimul[1] = 1
        c.act_simul()
        self.assertEqual(s.simul_total, 0)
        self.assertEqual(s.actingsingle[1], 1)
        self.assertEqual(s.enemies[0].actconnoe, 0)

    def test_normal_menu_selection_sets_registered_simul_flag(self):
        c = make(party=(1, 2))
        c.register_acts(0, 1, [CombatOption('Group ACT', simultaneous=True)])
        select_act(c)
        s = c.state
        self.assertEqual((s.acting_flags[0],s.actingsimul[0],s.acting_choice[0]), (1,1,0))
        c.handle_key('Left')
        c.handle_key('z')
        self.assertEqual(s.resolution_stage, 'act_simul')
        self.assertEqual(s.simul_orders, {1:0})

    def test_simul_callback_receives_prepared_orders(self):
        events = []
        c = make(party=(1,2), on_act_simul=lambda s: events.append((s.simul_orders.copy(),s.simul_total)))
        c.register_acts(0, 2, [CombatOption('Synergy', simultaneous=True)])
        c.state.actingsingle[1] = 1
        c.state.actingtarget[1] = 0
        c.act_simul()
        self.assertEqual(events, [({2:0},1)])


class IntegrationSourceTests(unittest.TestCase):
    def test_game_handoff_connects_all_new_resolution_callbacks(self):
        source = Path(__file__).with_name('game.py').read_text(encoding='utf8')
        cls = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == 'Game')
        fn = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_battle_controller_handoff')
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and
                 isinstance(n.func, ast.Name) and n.func.id == 'BattleCombatController']
        self.assertEqual(len(calls), 1)
        names = {kw.arg for kw in calls[0].keywords}
        self.assertTrue({'on_attack_press_start','on_spell_phase_start','on_act_started'} <= names)

    def test_gml_method_aliases_are_exposed(self):
        c = make()
        self.assertEqual(c.scr_attackphase.__func__, c.attack_phase.__func__)
        self.assertEqual(c.scr_nextact.__func__, c.next_act.__func__)
        self.assertEqual(c.scr_act_simul.__func__, c.act_simul.__func__)


if __name__ == '__main__':
    unittest.main()
