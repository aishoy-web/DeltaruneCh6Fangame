"""Recovered scr_monster_statreset / makeinstance / mnendturn regression tests."""
import unittest
from math import ceil

from battle_combat import BattleCombatController
from battle_monsters import MonsterHooks, MonsterSlotState, scr_monster_statreset
from encounter_setup import setup_encounter


def combat(encounter=1, party=(1,), **kwargs):
    return BattleCombatController(setup_encounter(encounter, party), party, {}, **kwargs)


class MonsterPortTests(unittest.TestCase):
    def test_all_19_source_statreset_values_cleared(self):
        slot = MonsterSlotState(2)
        slot.monster = 1
        slot.monsterx, slot.monstery = 123, 45
        slot.monstername = 'Enemy'
        slot.monsterhp, slot.monstermaxhp = 100, 200
        slot.monstergold = 333
        slot.mercymod = 70
        slot.monstercomment = 'Comment'
        slot.monsterstatus = 1
        slot.talked = 1
        scr_monster_statreset(slot)
        self.assertEqual(slot.index, 2)
        self.assertEqual(slot.monster, 0)
        self.assertEqual((slot.monsterx, slot.monstery), (0, 0))
        self.assertEqual((slot.monstername, slot.monstercomment), (' ', ' '))
        self.assertEqual((slot.monsterhp, slot.monstermaxhp), (0, 0))
        self.assertEqual((slot.monstergold, slot.mercymod, slot.monsterstatus, slot.talked), (0, 0, 0, 0))
        self.assertIsNone(slot.monsterinstance)

    def test_all_three_slots_reset_including_empty_and_actreset_callback(self):
        calls = []
        c = combat(203, monster_hooks={'*': MonsterHooks(act_reset=lambda slot: calls.append(slot.index))})
        self.assertEqual(calls, [0, 1, 2])
        self.assertEqual([slot.monster for slot in c.state.monster_slots], [1, 1, 0])
        self.assertIsNone(c.state.monster_slots[2].monsterinstance)
        self.assertEqual(c.state.monster_slots[2].monstername, ' ')
        self.assertEqual(c.state.monster_slots[0].monsterhp, 0)
        self.assertIsNone(c.state.enemies[0].hp)  # 0 from reset is NOT real HP

    def test_event_user12_then_15_per_instance_and_slot_identity(self):
        seen = []
        def user12(enemy):
            seen.append((enemy.slot, 12))
            enemy.name = 'Test Enemy'
            enemy.hp = 10
            enemy.max_hp = 25
        def user15(enemy):
            seen.append((enemy.slot, 15))
            enemy.mercy = 35
        c = combat(1, monster_hooks={'obj_baseenemy': MonsterHooks(
            event_user_12=user12, event_user_15=user15)})
        self.assertEqual(seen, [(0,12), (0,15), (1,12), (1,15)])
        for index in (0, 1):
            slot = c.state.monster_slots[index]
            self.assertIs(slot.monsterinstance, c.state.enemies[index])
            self.assertEqual((slot.monstername, slot.monsterhp, slot.monstermaxhp, slot.mercymod),
                             ('Test Enemy', 10, 25, 35))
            self.assertEqual(slot.monster, 1)
        self.assertEqual(c.state.enemies[1].slot, 1)

    def test_set_enemy_stats_updates_gml_slot_and_status(self):
        c = combat()
        c.set_enemy_stats(0, name='Target', hp=10, max_hp=20, mercy=100, tired=True)
        m = c.state.monster_slots[0]
        self.assertEqual((m.monstername, m.monsterhp, m.monstermaxhp, m.mercymod, m.monsterstatus),
                         ('Target', 10, 20, 100, 1))
        with self.assertRaises(IndexError):
            c.set_enemy_stats(2, hp=20)

    def test_enemy_removal_and_winfight_callback_once(self):
        called = []
        c = combat(on_wincombat=lambda state: called.append(state.encounter_no))
        c.deactivate_enemy(0)
        self.assertEqual(c.state.monster_slots[0].monster, 0)
        c.deactivate_enemy(1)
        self.assertEqual(c.state.phase, 'command')  # not victory until turn ends
        c.mn_end_turn()
        self.assertEqual(c.state.phase, 'victory')
        self.assertEqual(called, [1])
        self.assertEqual(c.state.victory, 1)
        c.mn_end_turn()
        self.assertEqual(called, [1])

    def test_victory_flag39_also_requests_win_without_deleting_monsters(self):
        c = combat()
        c.flags[39] = 1
        c.mn_end_turn()
        self.assertEqual(c.state.phase, 'victory')
        self.assertEqual(len([e for e in c.state.enemies if e.active]), 0)

    def test_regular_endturn_reset_call_order_and_enemy_flags(self):
        events = []
        hook = MonsterHooks(end_turn_action=lambda enemy: events.append(('end', enemy.slot)))
        c = combat(monster_hooks={'obj_baseenemy': hook},
                   on_cursor_memory_reset=lambda s: events.append(('cursor', s.charturn)))
        s = c.state
        s.messagepriority = 4
        s.attackpriority = 5
        s.mnfight = 2
        s.myfight = 5
        s.bmenuno = 11
        s.tension = 40
        s.charturn = 0
        s.monsterattackname = ['A', 'B', 'C']
        s.charaction = [1, 1, 1]
        s.actingtarget = [2, 2, 2]
        s.hittarget = [1, 1, 1]
        s.enemies[0].attacked = 1
        s.enemies[1].talked = 1
        s.actors[0].tu = 2
        c.mn_end_turn()
        self.assertEqual(events, [('cursor', 0), ('end', 0), ('end', 1)])
        self.assertEqual((s.messagepriority, s.attackpriority, s.mnfight, s.myfight, s.bmenuno, s.charturn),
                         (-1, -1, 0, 0, 0, 0))
        self.assertEqual(s.phase, 'command')
        self.assertEqual(s.charaction, [0] * 3)
        self.assertEqual(s.hittarget, [0] * 3)
        self.assertEqual(s.actingtarget, [0] * 3)
        self.assertEqual(s.monsterattackname, [' '] * 3)
        self.assertEqual(s.actors[0].tu, 0)
        self.assertEqual(s.temptension, [40] * 3)
        self.assertEqual((s.enemies[0].attacked, s.enemies[1].talked), (0,0))

    def test_down_party_heals_one_eighth_ceiling_but_unknown_is_untouched(self):
        c = combat(party=(1, 2, 3), party_stats={
            1: {'hp': 0, 'max_hp': 65}, 2: {'hp': -1, 'max_hp': 40}})
        c.mn_end_turn()
        self.assertEqual((c.state.actors[0].hp, c.state.actors[1].hp), (9, 4))
        self.assertIsNone(c.state.actors[2].hp)
        self.assertEqual(c.state.pending_heals, [(0, ceil(65/8)), (1, ceil(40/8))])

    def test_heal_override_does_not_apply_fallback_heal_twice(self):
        called = []
        def heal(actor, amount):
            called.append((actor.slot, amount))
            actor.hp = 12
        c = combat(party_stats={1: {'hp': 0, 'max_hp': 80}}, on_heal=heal)
        c.mn_end_turn()
        self.assertEqual(c.state.actors[0].hp, 12)
        self.assertEqual(called, [(0,10)])

    def test_temporary_inventory_refresh_is_only_first_twelve_indices(self):
        c = combat(inventory=list(range(1,14)))
        c.state.tempitem[12][0] = 777
        c.replace_inventory(list(range(11,24)))
        c.mn_end_turn()
        self.assertEqual([c.state.tempitem[i][0] for i in range(12)], list(range(11,23)))
        self.assertEqual(c.state.tempitem[12][0], 777)

    def test_automatic_party_skipped_and_endturn_callback_when_all_auto(self):
        called = []
        c = combat(party=(1, 2), party_auto={1: 1, 2: 1},
                   on_endturn=lambda s: called.append(s.phase))
        c.mn_end_turn()
        self.assertEqual(c.state.phase, 'awaiting_resolution')
        self.assertEqual(c.state.charturn, 3)
        self.assertEqual(called, ['awaiting_resolution'])
        d = combat(party=(1,2), party_auto={1:1})
        d.mn_end_turn()
        self.assertEqual(d.state.charturn, 1)
        self.assertEqual(d.state.phase, 'command')

    def test_alarm2_endturn_15_full_frames_after_attack_phase(self):
        c = combat()
        c.begin_enemy_turn(1)
        c.update(1)
        self.assertEqual(c.state.phase, 'enemy_turn')
        self.assertEqual(c.state.timer_alarm2, 15)
        c.update(14)
        self.assertEqual(c.state.timer_alarm2, 1)
        c.update(1)
        self.assertEqual(c.state.phase, 'command')
        self.assertEqual(c.state.timer_alarm2, None)


if __name__ == '__main__':
    unittest.main()
