"""scr_endturn + scr_wincombat ports; source-driven boundary tests."""
import ast
import unittest
from math import floor
from pathlib import Path
from types import SimpleNamespace

from battle_combat import BattleCombatController, CombatOption
from battle_monsters import MonsterHooks
from encounter_setup import setup_encounter


def make(encounter=1, party=(1,), *, flags=None, **kwargs):
    flags = {} if flags is None else flags
    return BattleCombatController(setup_encounter(encounter, party), party, flags, **kwargs)


class EndTurnTests(unittest.TestCase):
    def test_queue_completion_calls_endturn_attackphase_hook_without_damage(self):
        actions, phases, commits = [], [], []
        c = make(on_actions_ready=lambda q: actions.extend(q),
                 on_turn_committed=lambda s: commits.append(s.phase),
                 on_attack_phase=lambda s: phases.append((s.phase, s.resolution_stage)))
        c.handle_key('z'); c.handle_key('z')
        self.assertEqual([q.kind for q in actions], ['fight'])
        self.assertEqual(commits, ['awaiting_resolution'])
        self.assertEqual(phases, [('awaiting_resolution', 'attack_press')])
        self.assertEqual(c.state.attacking, 1)
        self.assertEqual(c.state.victory, 0)
        self.assertIsNone(c.state.enemies[0].hp)

    def test_kris_act_waits_for_enemy_event_not_next_act(self):
        act, attack = [], []
        c = make(on_next_act=lambda s: act.append(s.resolution_stage),
                 on_attack_phase=lambda s: attack.append('attack'))
        c.register_acts(0, 1, [CombatOption('Check')])
        c.handle_key('Right'); c.handle_key('z'); c.handle_key('z'); c.handle_key('z')
        self.assertEqual(c.state.myfight, 3)
        self.assertEqual(c.state.charturn, 3)
        self.assertEqual(c.state.resolution_stage, 'act')
        self.assertEqual(act, [])
        self.assertEqual(c.state.enemies[0].actcon, 1)
        self.assertFalse(attack)
        self.assertEqual(c.state.queued[0].kind, 'act')

    def test_simultaneous_act_and_active_actor_without_simul_have_distinct_routes(self):
        events = []
        c = make(on_act_simul=lambda s: events.append('simul'),
                 on_next_act=lambda s: events.append('next'))
        c.state.acting_flags[0] = c.state.actingsimul[0] = 1
        c.end_turn()
        self.assertEqual((c.state.resolution_stage, events), ('act_simul', ['simul']))
        d = make(on_next_act=lambda s: events.append('bad'))
        d.state.acting_flags[0] = 1
        d.end_turn()
        self.assertEqual(d.state.resolution_stage, 'act')
        self.assertEqual(events, ['simul'])

    def test_inventory_is_committed_from_charturn_column_and_broadcast_0_11(self):
        captured = []
        c = make(party=(1,2), inventory=list(range(1,14)),
                 on_turn_committed=lambda s: captured.append(tuple(c.inventory_snapshot())))
        s = c.state
        s.charturn = 1
        s.tempitem[0][1] = 99
        s.tempitem[4][1] = 88
        s.tempitem[12] = [551, 552, 553]
        c.end_turn()
        self.assertEqual(c.inventory_snapshot()[0], 99)
        self.assertEqual(c.inventory_snapshot()[4], 88)
        self.assertEqual(c.inventory_snapshot()[12], 13)
        self.assertEqual(s.tempitem[0], [99,99,99])
        self.assertEqual(s.tempitem[4], [88,88,88])
        self.assertEqual(s.tempitem[12], [551,552,553])
        self.assertEqual(captured[0][0], 99)
        self.assertEqual(s.moveswapped, 0)

    def test_repeated_endturn_is_idempotent_while_awaiting_resolution(self):
        called = []
        c = make(on_attack_phase=lambda s: called.append(1))
        c.end_turn()
        c.end_turn()
        self.assertEqual(called, [1])

    def test_no_valid_tempitem_column_on_all_auto_preserves_inventory(self):
        c = make(inventory=[11, 22], party_auto={1:1})
        c.state.charturn = 3
        c.end_turn()
        self.assertEqual(c.inventory_snapshot()[:2], (11,22))
        self.assertEqual(c.state.resolution_stage, 'attack_press')

    def test_defend_armor_38_heals_16_percent_at_endturn(self):
        heals = []
        c = make(party=(1, 4), equipped_armors={2:(38, 0)},
                 party_stats={4:{'hp':20,'max_hp':101}},
                 on_heal=lambda actor,amount:(heals.append((actor.character_id, amount)), setattr(actor,'hp', min(actor.max_hp, actor.hp+amount))))
        s = c.state
        s.faceaction[1] = 4
        s.actors[1].tu = 7
        c.end_turn()
        self.assertEqual(heals, [(4, 16)])
        self.assertEqual(s.actors[1].hp, 36)
        self.assertEqual(s.actors[1].tu, 5)  # +1 healing, then 3 decrements
        self.assertEqual(s.pending_turn_heals, [(1,16)])

    def test_armor_38_does_not_heal_without_defend(self):
        c = make(equipped_armors={1:(38,)}, party_stats={1:{'hp':12,'max_hp':100}})
        c.end_turn()
        self.assertEqual(c.state.actors[0].hp, 12)
        self.assertEqual(c.state.pending_turn_heals, [])

    def test_auto_target_prefers_lowest_occupied_monster_index(self):
        c = make(party_auto={1:1})
        c.deactivate_enemy(0)
        c.end_turn()
        self.assertEqual(c.state.chartarget[0], 1)

    def test_endturn_resets_priority_and_monster_attack_names(self):
        c = make()
        s = c.state
        s.messagepriority, s.attackpriority = 7, 8
        s.monsterattackname = ['Bite', 'Smash', ' ']
        c.end_turn()
        self.assertEqual((s.messagepriority, s.attackpriority), (-1,-1))
        self.assertEqual(s.monsterattackname, [' ']*3)

    def test_enemy_phase_refuses_recommitting(self):
        c = make()
        c.begin_enemy_turn()
        c.end_turn()
        self.assertEqual(c.state.phase, 'enemy_turn')
        self.assertIsNone(c.state.resolution_stage)

    def test_on_endturn_notification_after_attackphase(self):
        events = []
        c = make(on_attack_phase=lambda s: events.append('attack'),
                 on_endturn=lambda s: events.append('committed'))
        c.end_turn()
        self.assertEqual(events, ['attack', 'committed'])


class WinCombatTests(unittest.TestCase):
    def test_normal_win_marks_victory_and_pays_registered_rewards_once(self):
        events = []
        c = make(monster_hooks={'obj_baseenemy': MonsterHooks(monster_defeat=lambda e: events.append(e.slot))},
                 on_wincombat=lambda s: events.append('win'))
        s = c.state
        s.reward_gold, s.reward_exp = 34, 7
        s.tension = 20
        c.win_combat()
        self.assertEqual(events, [0,1,'win'])
        self.assertEqual(s.phase, 'victory')
        self.assertEqual((s.myfight, s.mnfight, s.battleend), (7,-1,1))
        self.assertEqual((s.reward_gold, s.reward_exp), (46,7))  # 34 + floor(20/10)*6
        self.assertEqual((s.gold, s.xp), (46,7))
        c.win_combat()
        self.assertEqual(events, [0,1,'win'])

    def test_flag36_forces_normal_victory_despite_60(self):
        flags = {60:203}
        c = make(flags=flags)
        c.flags[36] = 1  # Create resets this flag, so set it after initialization.
        c.win_combat()
        self.assertEqual(c.state.phase, 'victory')
        self.assertEqual(c.state.encounter_no, 1)
        self.assertEqual(flags[60], 203)

    def test_flag39_ends_battle_and_skips_60_branch_only_if_flag36(self):
        c = make(flags={60:203})
        c.flags[39] = 1
        c.mn_end_turn()
        self.assertEqual(c.state.phase, 'chained_encounter')
        self.assertEqual(c.state.encounter_no, 203)

    def test_chained_encounter_resets_flag60_and_moves_enemies_from_x800(self):
        events = []
        c = make(flags={60:203},
                 on_chained_encounter=lambda s,layout: events.append((s.encounter_no,layout.number)))
        c.deactivate_enemy(0)
        c.deactivate_enemy(1)
        c.mn_end_turn()
        s = c.state
        self.assertEqual(events, [(203,203)])
        self.assertEqual(c.flags[60], 0)
        self.assertEqual((s.victory, s.myfight, s.mnfight), (0,5,-1))
        self.assertEqual(s.phase, 'chained_encounter')
        self.assertEqual(s.fight_return_timer, 15)
        self.assertEqual(len(s.enemies), 2)
        self.assertEqual([e.x for e in s.enemies], [800,800])
        self.assertEqual([e.entrance_frames for e in s.enemies], [10,10])
        c.update(9)
        self.assertNotEqual(s.enemies[0].x, 473)
        c.update(1)
        self.assertEqual([(e.x, e.y) for e in s.enemies], [(473,50),(520,160)])
        self.assertEqual(s.phase, 'chained_encounter')
        c.update(4)
        self.assertEqual(s.phase, 'chained_encounter')
        c.update(1)
        self.assertEqual(s.phase, 'command')
        self.assertEqual((s.mnfight, s.myfight, s.charturn), (0,0,0))

    def test_wave_hooks_fired_12_then_15_in_new_wave(self):
        events = []
        hooks = MonsterHooks(event_user_12=lambda e:events.append((e.slot,12)),
                             event_user_15=lambda e:events.append((e.slot,15)))
        c = make(flags={60:203}, monster_hooks={'obj_shinobeetle_enemy':hooks})
        c.win_combat()
        self.assertEqual(events, [(0,12),(0,15),(1,12),(1,15)])
        self.assertIs(c.state.monster_slots[0].monsterinstance, c.state.enemies[0])
        self.assertIsNone(c.state.monster_slots[2].monsterinstance)

    def test_chained_wave_preserves_party_actor_locations_and_current_music(self):
        c = make(flags={60:204}, party=(1,2), music='battle.ogg')
        starting_positions = [(a.x,a.y) for a in c.state.actors]
        c.win_combat()
        self.assertEqual([(a.x,a.y) for a in c.state.actors], starting_positions)
        self.assertEqual(c.state.battle_music, 'battle.ogg')
        self.assertEqual(c.state.party_ids, (1,2,0))

    def test_chain_then_normal_victory(self):
        c = make(flags={60:203})
        c.win_combat()
        c.update(15)
        self.assertEqual(c.state.phase, 'command')
        c.win_combat()
        self.assertEqual(c.state.phase, 'victory')
        self.assertEqual(c.state.encounter_no, 203)

    def test_ongoing_wave_does_not_respawn_every_frame(self):
        c = make(flags={60:203})
        c.win_combat()
        instances = list(c.state.enemies)
        c.update(9)
        self.assertTrue(all(a is b for a,b in zip(instances,c.state.enemies)))
        self.assertEqual(c.state.victory, 0)

    def test_only_active_enemies_receive_defeat_hooks(self):
        events = []
        c = make(monster_hooks={'*':MonsterHooks(monster_defeat=lambda e:events.append(e.slot))})
        c.deactivate_enemy(0)
        c.win_combat()
        self.assertEqual(events, [1])

    def test_zero_flag60_no_chain(self):
        c = make(flags={60:0})
        c.win_combat()
        self.assertEqual(c.state.phase, 'victory')
        self.assertIsNone(c.state.pending_chained_encounter)


class GameAdaptorTests(unittest.TestCase):
    def test_view_layout_changes_without_replacing_live_battle(self):
        src = Path(__file__).with_name('game.py').read_text()
        klass = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == 'Game')
        funcs = [n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name in
                 ('_battle_turn_committed','_battle_chained_encounter')]
        child = ast.ClassDef(name='Fragment', bases=[], keywords=[], body=funcs, decorator_list=[])
        ns = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[child],type_ignores=[])), 'x','exec'), ns)
        game = ns['Fragment']()
        game.combat = make(inventory=[40,41])
        game.battle_view = SimpleNamespace(start=lambda l:setattr(game,'view_layout',l))
        game.battle_action_queue = [1]
        layout = setup_encounter(203)
        game._battle_chained_encounter(game.combat.state,layout)
        self.assertIs(game.battle_layout,layout)
        self.assertIs(game.view_layout,layout)
        self.assertEqual(game.battle_action_queue,[])
        game._battle_turn_committed(game.combat.state)
        self.assertEqual(game.battle_inventory[:2],[40,41])


if __name__ == '__main__':
    unittest.main()
