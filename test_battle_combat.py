"""Regression checks for obj_battlecontroller port (headless)."""
import unittest
from types import SimpleNamespace
from battle_combat import BattleCombatController, CombatOption
from encounter_setup import setup_encounter
from battle_view import BattleCanvasView
from battle import BattleController, PartySpawn


def make(encounter=1, party=(1,), **kwargs):
    layout = setup_encounter(encounter, party)
    return BattleCombatController(layout, party, {}, **kwargs)


class CombatCreateTests(unittest.TestCase):
    def test_create_init_fields_for_3_slots(self):
        c = make(228, (1, 2, 3))
        s = c.state
        self.assertEqual(s.chartotal, 3)
        self.assertEqual(s.havechar, [1, 1, 1, 0])
        self.assertEqual(s.charpos, [0, 1, 2, -1])
        self.assertEqual(s.charmove, [1, 1, 1])
        self.assertEqual(s.charcantarget, [1, 1, 1])
        self.assertEqual(s.bmenuno, 0)
        self.assertEqual(s.turntimer, 120)
        self.assertEqual(s.spelldelay, 10)
        self.assertEqual(s.tension, 0)
        self.assertEqual(s.battleend, 0)
        self.assertEqual(len(s.bmenucoord), 20)
        self.assertEqual(len(s.bmenucoord[0]), 20)
        self.assertEqual(len(s.battlespell[0]), 18)

    def test_empty_party_slots_and_chara_order(self):
        c = make(1, (1, 4))
        self.assertEqual(c.state.party_ids, (1, 4, 0))
        self.assertEqual(c.state.havechar, [1, 0, 0, 1])
        self.assertEqual(c.state.charpos, [0, -1, -1, 1])
        self.assertEqual(c.state.charmove, [1, 1, 0])

    def test_reset_flags_without_overwriting_unrelated_story_flag(self):
        layout = setup_encounter(1)
        flags = {34: 1, 9: 1, 50: 4, 53: 9, 63: 7, 36: 8, 39: 9, 62: 1}
        c = BattleCombatController(layout, (1,), flags)
        self.assertEqual(flags[34], 1)
        self.assertEqual(flags[9], 1)
        for k in (50, 51, 52, 53, 63, 36, 39, 62):
            self.assertEqual(flags[k], 0)
        self.assertEqual(c.state.fc, 0)

    def test_special_encounter_73_sets_face_fields(self):
        c = make(73)
        self.assertEqual((c.state.fc, c.state.fe), (3, 4))
        self.assertEqual(c.flags[62], 0)

    def test_ambush_sets_first_strike_and_quarter_tp(self):
        c = make(1, ambush=2, max_tension=125)
        self.assertEqual(c.state.tension, 31)
        self.assertTrue(all(e.first_strike for e in c.state.enemies))
        self.assertEqual(len(c.state.enemies), 2)

    def test_dark_world_stats_explicit_and_do_not_infer_light_world(self):
        c = make(1, party_stats={1: {"hp": 70, "max_hp": 100,
                                     "attack": 13, "defense": 7, "magic": 2}})
        self.assertEqual(c.state.battleat[0], 13)
        self.assertEqual(c.state.battledf[0], 7)
        self.assertEqual(c.state.battlemag[0], 2)
        self.assertEqual(c.state.actors[0].hp, 70)
        blank = make(1)
        self.assertIsNone(blank.state.actors[0].hp)
        self.assertIsNone(blank.state.enemies[0].hp)

    def test_items_per_party_slot_are_snapshotted_separately(self):
        c = make(1, (1, 2), inventory=[2, 19, 7])
        self.assertEqual([c.state.tempitem[i][0] for i in range(4)], [2, 19, 7, 0])
        self.assertEqual([c.state.tempitem[i][1] for i in range(4)], [2, 19, 7, 0])
        self.assertEqual(len(c.state.tempitem), 13)

    def test_enemy_stats_can_be_filled_by_missing_enemy_create_port(self):
        c = make(1)
        c.set_enemy_stats(0, hp=15, max_hp=40, mercy=70, tired=True, name="Dummy")
        self.assertEqual((c.state.enemies[0].hp, c.state.enemies[0].max_hp), (15, 40))
        self.assertEqual(c.state.enemies[0].mercy, 70)
        self.assertEqual(c.state.enemies[0].name, "Dummy")


class CombatInputTests(unittest.TestCase):
    def test_five_commands_wrap_and_back(self):
        c = make()
        c.handle_key("Left")
        self.assertEqual(c.state.bmenucoord[0][0], 4)
        c.handle_key("Right")
        self.assertEqual(c.state.bmenucoord[0][0], 0)
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 1)
        c.handle_key("x")
        self.assertEqual(c.state.bmenuno, 0)

    def test_enemy_target_wrap_fight_queues_without_fake_damage(self):
        c = make(1)
        c.handle_key("z")  # FIGHT -> target enemy
        c.handle_key("Up")  # Wrap from slot 0 to 1.
        self.assertEqual(c.state.bmenucoord[1][0], 1)
        c.handle_key("z")
        self.assertEqual(c.state.queued[0].kind, "fight")
        self.assertEqual(c.state.queued[0].target_slot, 1)
        self.assertEqual(c.state.phase, "awaiting_resolution")
        self.assertIsNone(c.state.enemies[0].hp)
        self.assertTrue(c.state.enemies[0].active)
        self.assertEqual(c.state.victory, 0)

    def test_defend_adds_40_tp_and_advances_to_next_member(self):
        c = make(1, (1, 2))
        c.handle_key("Left")  # DEFEND
        c.handle_key("z")
        self.assertEqual(c.state.tension, 40)
        self.assertEqual(c.state.charturn, 1)
        self.assertEqual(c.state.charaction[0], 10)
        self.assertEqual(c.state.faceaction[0], 4)
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 1)
        c.handle_key("z")
        self.assertEqual(c.state.phase, "awaiting_resolution")
        self.assertEqual([q.kind for q in c.state.queued[:2]], ["defend", "fight"])

    def test_krist_act_flow_target_then_act(self):
        c = make(1)
        c.register_acts(0, 1, [CombatOption("Check", description="Inspect")])
        c.handle_key("Right")
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 11)
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 9)
        c.handle_key("z")
        self.assertEqual(c.state.phase, "awaiting_resolution")
        self.assertEqual(c.state.queued[0].kind, "act")
        self.assertEqual(c.state.queued[0].target_slot, 0)

    def test_act_missing_data_not_fake_success(self):
        c = make()
        c.handle_key("Right")
        c.handle_key("z")
        c.handle_key("z")
        c.handle_key("z")
        self.assertIsNone(c.state.queued[0])
        self.assertEqual(c.state.bmenuno, 9)
        self.assertEqual(c.state.phase, "command")

    def test_spare_targets_enemy_and_does_not_victory_without_mercy_logic(self):
        c = make(1)
        for _ in range(3):
            c.handle_key("Right")
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 12)
        c.handle_key("z")
        self.assertEqual(c.state.queued[0].kind, "spare")
        self.assertEqual(c.state.charspecial[0], 100)
        self.assertEqual(c.state.victory, 0)

    def test_spells_are_optional_and_require_tp(self):
        c = make(1, (1, 2))
        heal = CombatOption("Heal", code=2, tp_cost=40, target=1)
        c.register_spells(1, [heal])
        self.assertEqual(c.state.battlespell[1][0], 2)
        c.handle_key("z")  # Kris fights
        c.handle_key("z")
        self.assertEqual(c.state.charturn, 1)
        c.handle_key("Right")  # ACT/MAGIC
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 2)
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 2)
        self.assertEqual(c.state.feedback, "Not enough TP.")
        c.state.tension = 60
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 8)
        c.handle_key("Down")
        self.assertEqual(c.state.bmenucoord[8][1], 1)
        c.handle_key("z")
        self.assertEqual(c.state.queued[1].kind, "spell")
        self.assertEqual(c.state.queued[1].target_slot, 1)
        self.assertEqual(c.state.tension, 20)

    def test_register_item_uses_dark_world_inventory_and_target(self):
        c = make(1, inventory=[25])
        c.register_item(25, CombatOption("Potion", target=1))
        c.handle_key("Right")
        c.handle_key("Right")
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 4)
        c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 7)
        c.handle_key("z")
        self.assertEqual(c.state.queued[0].kind, "item")
        self.assertEqual(c.state.queued[0].item_slot, 0)
        self.assertEqual(c.state.queued[0].target_slot, 0)

    def test_cancel_defend_restores_earlier_tp_for_previous_character(self):
        c = make(1, (1, 2))
        c.handle_key("Left")
        c.handle_key("z")
        self.assertEqual(c.state.tension, 40)
        c.handle_key("x")
        self.assertEqual(c.state.charturn, 0)
        self.assertEqual(c.state.tension, 0)
        self.assertIsNone(c.state.queued[0])

    def test_completed_queue_callback_and_explicit_next_turn(self):
        got = []
        c = make(1, on_actions_ready=lambda actions: got.extend(actions))
        c.handle_key("Left")
        c.handle_key("z")
        self.assertEqual(len(got), 1)
        self.assertEqual(c.state.phase, "awaiting_resolution")
        c.handle_key("Right")
        self.assertEqual(c.state.phase, "awaiting_resolution")
        c.reset_turn()
        self.assertEqual(c.state.phase, "command")
        self.assertEqual(c.state.charturn, 0)

    def test_missing_spells_not_invented(self):
        c = make(1, (1, 2))
        c.handle_key("z"); c.handle_key("z")
        c.handle_key("Right"); c.handle_key("z")
        self.assertEqual(c.state.bmenuno, 2)
        c.handle_key("z")
        self.assertEqual(c.state.phase, "command")
        self.assertEqual(c.state.feedback, "That action has no loaded definition.")


class VictoryAndTimerTests(unittest.TestCase):
    def test_victory_base_tp_reward_and_xp(self):
        layout = setup_encounter(1)
        flags = {37: 0}
        finished = []
        c = BattleCombatController(layout, (1,), flags, on_victory_finished=lambda s: finished.append(s.gold))
        c.state.tension = 45
        c.begin_victory(monster_gold=20, monster_exp=10)
        self.assertEqual(c.state.reward_gold, 44)  # 20 + floor(45/10)*6
        self.assertEqual(c.state.xp, 10)
        self.assertEqual(c.state.victory, 1)
        self.assertEqual(c.state.phase, "victory")
        c.update(100)
        self.assertFalse(finished)  # Must dismiss text.
        c.handle_key("z")
        c.update(10)
        self.assertEqual(finished, [44])
        c.update(100)
        self.assertEqual(finished, [44])

    def test_victory_armor_and_weapon_bonus_and_flag_37(self):
        c = make()
        c.begin_victory(monster_gold=100, equipped_weapons={1: 8},
                        armor_counts={8: 1, 21: 1})
        # 100 + 5 weapon bonus; 105 * 1.05 * 1.3 = 143.325 -> floor 143.
        self.assertEqual(c.state.reward_gold, 143)
        d = make()
        d.flags[37] = 1
        d.begin_victory(monster_gold=999)
        self.assertEqual(d.state.reward_gold, 0)
        self.assertEqual(d.state.victory_message, "* You won the battle!")

    def test_revival_and_levelup_flag(self):
        flags = {63: 1}
        c = BattleCombatController(setup_encounter(1, (1, 4)), (1, 4), flags,
                                   party_stats={1: {"hp": 0, "max_hp": 72}})
        # Create clears flag 63. Monster logic will set it on a real level-up.
        self.assertEqual(c.flags[63], 0)
        c.flags[63] = 1
        called = []
        c.begin_victory(monster_gold=30, level_up=lambda: called.append(1))
        self.assertEqual(c.state.actors[0].hp, 9)
        self.assertIn("Noelle became stronger", c.state.victory_message)
        self.assertEqual(called, [1])

    def test_screen_intro_reaches_152_and_enemy_turn_alarm_calls_mnendturn(self):
        c = make()
        self.assertEqual(c.state.bp, 0)
        c.update(20)
        self.assertEqual(c.state.bp, 152)
        self.assertEqual(c.state.intro, 0)
        c.begin_enemy_turn(3)
        c.update(3)
        self.assertEqual(c.state.reset, 1)
        c.update(14)
        self.assertEqual(c.state.mnfight, 2)  # 15 frames after scheduling.
        c.update(1)
        self.assertEqual(c.state.mnfight, 0)
        self.assertEqual(c.state.phase, "command")

    def test_victory_cannot_be_triggered_from_merely_selecting_fight(self):
        c = make()
        c.handle_key("z"); c.handle_key("z")
        self.assertEqual(c.state.victoried, 0)
        self.assertEqual(c.state.reward_gold, 0)


class CombatCanvasTests(unittest.TestCase):
    def test_hud_draws_command_row_and_menu_selection_in_preview(self):
        class Canvas:
            def __init__(self): self.actions = []
            def winfo_width(self): return 640
            def winfo_height(self): return 480
            def delete(self, tag): pass
            def create_rectangle(self, *args, **kw): self.actions.append(("rect", kw))
            def create_text(self, *args, **kw): self.actions.append(("text", kw))
            def tag_raise(self, tag): pass
        canvas = Canvas()
        game = SimpleNamespace(canvas=canvas, scale=2, ui_to_screen=lambda x,y:(2*x,2*y))
        view = BattleCanvasView(game)
        layout = setup_encounter(1)
        view.start(layout)
        entry = BattleController().start_battle(1, 0, layout.enemy_slots, {},
                                                party_members=[PartySpawn(1, 0, 0, 80, 140)])
        entry.controller_started = True
        combat = make()
        combat.update(20)
        view.render(entry, combat)
        names = [kw.get("text", "") for cmd, kw in canvas.actions if cmd == "text"]
        for command in ("FIGHT", "ACT", "ITEM", "SPARE", "DEFEND"):
            self.assertIn(command, names)
        self.assertIn("Kris  --/--", names)
        combat.handle_key("z")
        view.render(entry, combat)
        names = [kw.get("text", "") for cmd, kw in canvas.actions if cmd == "text"]
        self.assertTrue(any("Baseenemy" in name or "Base Enemy" in name for name in names))


if __name__ == "__main__":
    unittest.main()

class AdditionalSourceRulesTests(unittest.TestCase):
    def test_weapon_35_bonus_only_third_party_slot_when_stats_exist(self):
        c = make(1, (1, 2, 3),
                 equipped_weapons={3: 35},
                 party_stats={3: {"attack": 10, "defense": 4, "magic": 5}})
        self.assertEqual(c.state.battleat[2], 22)
        self.assertEqual(c.state.battledf[2], 7)
        self.assertEqual(c.state.battlemag[2], 8)
        self.assertIsNone(c.state.battleat[0])

    def test_special_stream_volume_rule(self):
        layout = setup_encounter(1)
        c = BattleCombatController(layout, (1,), {}, music="boss.ogg", active_stream_song="boss.ogg")
        self.assertEqual(c.state.battle_music_volume, 1.0)
        d = BattleCombatController(layout, (1,), {}, music="battle.ogg", active_stream_song="battle.ogg")
        self.assertEqual(d.state.battle_music_volume, 0.7)

    def test_ambush_one_needs_external_scr_ambush(self):
        c = make(1, ambush=1)
        self.assertEqual(c.state.pending_ambush, 1)
        self.assertEqual(c.state.tension, 0)
