"""Regression tests for the Chapter 5 scr_battle -> Python port."""

import unittest

from battle import BattleController, EnemyMarker, EnemySpawn, PartySpawn


class BattleStartTests(unittest.TestCase):
    def enemy(self, *, sprite="spr_test", kind=1):
        return EnemySpawn(monster_type=kind, x=120, y=80, sprite=sprite)

    def test_spawn_position_tween_and_doom_timer(self):
        flags = {}
        alarms = []
        manager = BattleController(on_doom_alarm=lambda doom, state: alarms.append(doom))
        battle = manager.start_battle(17, 0, [self.enemy()], flags)
        marker = battle.markers[0]
        self.assertEqual(flags[9], 1)
        self.assertEqual(battle.music_to_load, "battle.ogg")
        self.assertEqual((marker.x, marker.y, marker.depth, marker.enemy_slot), (420, 80, 0, 0))
        manager.update(10)
        self.assertEqual((marker.x, marker.y), (270, 80))
        manager.update(10)
        self.assertEqual((marker.x, marker.y), (120, 80))
        self.assertFalse(battle.intro_complete)
        manager.update(5)
        self.assertTrue(battle.intro_complete)
        self.assertEqual(len(alarms), 1)
        manager.update(500)
        self.assertEqual(len(alarms), 1)

    def test_existing_marker_is_reused_without_resetting_depth(self):
        old = EnemyMarker(700, 90, sprite="spr_other", depth=9)
        manager = BattleController()
        battle = manager.start_battle(1, 1, [self.enemy()], [0] * 10, existing_markers=[old])
        self.assertIs(battle.markers[0], old)
        self.assertEqual(old.depth, 9)
        self.assertEqual((old.x, old.y), (700, 90))
        manager.update(20)
        self.assertEqual((old.x, old.y), (120, 80))

    def test_special_flag_preserves_music_and_flag(self):
        manager = BattleController()
        flags = {9: 2}
        battle = manager.start_battle(2, 0, [self.enemy()], flags)
        self.assertEqual(flags[9], 2)
        self.assertIsNone(battle.music_to_load)
        self.assertIsNone(manager.music)

    def test_special_sprites_and_chapter_five_music(self):
        manager = BattleController()
        battle = manager.start_battle(
            3, 0, [self.enemy(sprite="spr_shinobeetle")], [0] * 10, chapter=5
        )
        self.assertEqual(battle.music_to_load, "rakuichi_buster_wip.ogg")
        self.assertEqual(battle.doom_effects[0].remaining_frames, 24)
        manager.update(23)
        self.assertFalse(battle.doom_effects[0].triggered)
        manager.update(1)
        self.assertTrue(battle.doom_effects[0].triggered)

    def test_chapter_five_room_scaling_only(self):
        for chapter, expected in [(5, 1.5), (6, 1.0)]:
            manager = BattleController()
            battle = manager.start_battle(
                3, 0, [self.enemy(sprite="spr_kawkaw")], {}, chapter=chapter,
                room_id="room_dw_cliff_kawkawdash"
            )
            self.assertEqual(battle.markers[0].scale_x, expected)

    def test_three_slots_including_empty_and_missing_marker(self):
        manager = BattleController()
        dead = EnemyMarker(999, 999, "old", alive=False)
        battle = manager.start_battle(
            10, 0,
            [self.enemy(), self.enemy(kind=0), self.enemy()],
            {}, existing_markers=[None, None, dead]
        )
        self.assertEqual(len(battle.markers), 3)
        self.assertIsNone(battle.markers[1])
        self.assertEqual(battle.markers[2].depth, -2)
        self.assertEqual(len(battle.doom_effects), 2)

    def test_callbacks(self):
        events = []
        manager = BattleController(
            on_start=lambda state: events.append("start"),
            on_doom_alarm=lambda effect, state: events.append("doom"),
            on_intro_complete=lambda state: events.append("complete"),
        )
        manager.start_battle(1, 0, [self.enemy()], {})
        manager.update(25)
        self.assertEqual(events, ["start", "doom", "complete"])
        with self.assertRaises(RuntimeError):
            manager.start_battle(2, 0, [], {})
        manager.end_battle()
        manager.start_battle(2, 0, [], {})


class EncounterBasicTests(unittest.TestCase):
    @staticmethod
    def party():
        return [
            PartySpawn(1, 10, 20, 110, 120),
            PartySpawn(2, 30, 40, 130, 140, "spr_susier_dark", "susie", armed=False),
            PartySpawn(3, 50, 60, 150, 160, "spr_ralsei_dark", "ralsei"),
        ]

    @staticmethod
    def enemy(sprite="spr_test"):
        return EnemySpawn(1, 120, 80, sprite)

    def test_create_sequence_and_world_suspension_hooks(self):
        actions = []
        controller = BattleController(
            on_music_fade=lambda st, frames: actions.append(("fade", frames)),
            on_encounter_setup=lambda st: actions.append(("encounter", st.encounter_no)),
            on_suspend_overworld=lambda st: actions.append(("suspend", st.interact)),
            on_start=lambda st: actions.append(("start", len(st.party_markers))),
            on_music_pause=lambda st: actions.append(("pause", st.elapsed_frames)),
        )
        state = controller.start_battle(33, 0, [], {}, party_members=self.party())
        self.assertEqual(actions, [("fade", 20), ("encounter", 33),
                                   ("suspend", 2), ("start", 3)])
        self.assertTrue(state.platform_paused)
        self.assertTrue(state.overworld_suspended)
        self.assertEqual(state.interact, 2)
        self.assertEqual([mark.depth for mark in state.party_markers], [200, 180, 160])
        self.assertEqual(state.party_markers[0].sprite, "spr_kris_sword_jump_down")
        self.assertEqual(state.party_markers[1].sprite, "spr_susier_wall")
        controller.update(1)
        controller.update(9)
        self.assertEqual(actions.count(("pause", 1)), 1)

    def test_exact_10_frame_rush_and_24_frame_battlecontroller_handoff(self):
        afterimages = []
        sounds = []
        handoffs = []
        ends = []
        manager = BattleController(
            on_afterimage=lambda marker, st: afterimages.append((st.elapsed_frames, marker.party_index)),
            on_sound=lambda name, volume, st: sounds.append((name, volume, st.elapsed_frames)),
            on_controller_start=lambda st: handoffs.append(st.elapsed_frames),
            on_intro_complete=lambda st: ends.append(st.elapsed_frames),
        )
        st = manager.start_battle(7, 0, [self.enemy()], {}, party_members=self.party())
        manager.update(9)
        self.assertEqual(st.fightcon, 1)
        self.assertEqual(st.counttimer, 9)
        self.assertEqual(len(afterimages), 27)  # 3 members x 9 frames
        self.assertEqual((st.party_markers[0].x, st.party_markers[0].y), (100, 110))
        manager.update(1)
        self.assertEqual(st.fightcon, 2)
        self.assertEqual(st.counttimer, 1)  # Both GML if-blocks run on frame 10.
        self.assertEqual([m.sprite for m in st.party_markers], [
            "spr_krisb_attack", "spr_susieb_attack_unarmed", "spr_ralsei_battleintro",
        ])
        self.assertTrue(all(m.in_pose for m in st.party_markers))
        self.assertEqual((st.party_markers[0].x, st.party_markers[0].y), (110, 120))
        self.assertEqual(sounds, [("snd_impact", .7, 10),
                                  ("snd_weaponpull_fast", .8, 10)])
        manager.update(13)
        self.assertEqual(st.elapsed_frames, 23)
        self.assertFalse(st.controller_started)
        manager.update(1)
        self.assertEqual(st.fightcon, 3)
        self.assertEqual(handoffs, [24])
        self.assertTrue(st.controller_started)
        self.assertTrue(all(not m.alive for m in st.party_markers))
        self.assertFalse(st.intro_complete)  # Doom at 25, not at 24.
        manager.update(1)
        self.assertEqual(ends, [25])
        self.assertTrue(st.intro_complete)
        self.assertFalse(st.markers[0].alive)
        self.assertFalse(st.doom_effects[0].alive)
        manager.update(100)
        self.assertEqual(handoffs, [24])
        self.assertEqual(ends, [25])

    def test_climb_and_platform_mode_spawn_positions(self):
        manager = BattleController()
        st = manager.start_battle(
            2, 0, [], {}, party_members=self.party(),
            kris_platform_origin=(500, 600), kris_climb_origin=(800, 700),
        )
        self.assertEqual([(m.x, m.y) for m in st.party_markers], [(800, 700)] * 3)
        self.assertEqual([m.image_alpha for m in st.party_markers], [1.0, 0.0, 0.0])
        manager.update(10)
        self.assertAlmostEqual(st.party_markers[1].image_alpha, 0)
        manager.update(10)
        self.assertAlmostEqual(st.party_markers[1].image_alpha, 1)
        manager.end_battle()
        st2 = manager.start_battle(
            3, 0, [], {}, party_members=self.party(),
            kris_platform_origin=(500, 600),
        )
        self.assertEqual((st2.party_markers[0].x, st2.party_markers[0].y), (500, 600))
        self.assertEqual((st2.party_markers[1].x, st2.party_markers[1].y), (30, 40))

    def test_noelle_intro_sprite_and_frame_preservation(self):
        members = [
            self.party()[0],
            PartySpawn(4, 10, 20, 30, 40, "spr_noelle_dark", "noelle", sideb_phase=2),
            PartySpawn(4, 40, 60, 90, 70, "spr_noelle_dark", "noelle", sideb_phase=3),
        ]
        manager = BattleController()
        st = manager.start_battle(1, 0, [], {}, party_members=members)
        self.assertEqual(st.party_markers[1].sprite, "spr_noelleb_battleintro_sideb")
        self.assertEqual(st.party_markers[2].sprite, "spr_noelleb_battleintro")
        self.assertEqual(st.party_markers[1].image_speed, .5)
        st.party_markers[1].image_index = 5
        manager.update(10)
        self.assertEqual(st.party_markers[1].image_index, 10)
        self.assertEqual(st.party_markers[1].sprite, "spr_noelleb_battleintro_sideb")

    def test_chapter_five_ralsei_pose_exceptions(self):
        members = [self.party()[0], self.party()[2]]
        manager = BattleController()
        st = manager.start_battle(225, 0, [], {}, chapter=5, party_members=members)
        manager.update(10)
        self.assertEqual(st.party_markers[1].sprite, "spr_ralsei_begin_battle_serious")
        manager.end_battle()
        st = manager.start_battle(
            225, 0, [], {}, chapter=5, party_members=members,
            chapter5_flag_1311=True,
        )
        manager.update(10)
        self.assertEqual(st.party_markers[1].sprite, "spr_ralseib_battleintro")
        manager.end_battle()
        st = manager.start_battle(
            225, 0, [], {}, chapter=6, party_members=members,
            chapter5_flag_1311=True,
        )
        manager.update(10)
        self.assertEqual(st.party_markers[1].sprite, "spr_ralsei_battleintro")

    def test_special_encounter_84_omits_sounds_but_keeps_poses(self):
        sounds = []
        manager = BattleController(on_sound=lambda *args: sounds.append(args))
        st = manager.start_battle(84, 0, [], {}, party_members=self.party())
        manager.update(10)
        self.assertEqual(sounds, [])
        self.assertTrue(all(m.in_pose for m in st.party_markers))

    def test_special_encounter_230_omits_kris_marker_and_pose(self):
        sounds = []
        afterimages = []
        manager = BattleController(
            on_sound=lambda *args: sounds.append(args),
            on_afterimage=lambda marker, st: afterimages.append(marker.party_index),
        )
        st = manager.start_battle(230, 0, [], {}, party_members=self.party())
        self.assertFalse(st.party_markers[0].alive)
        manager.update(10)
        self.assertEqual(sounds, [])
        self.assertEqual(afterimages, [1, 2] * 9)
        self.assertFalse(st.party_markers[1].in_pose)
        self.assertEqual(st.party_markers[1].sprite, "spr_susier_wall")
        manager.update(14)
        self.assertTrue(st.controller_started)
        self.assertEqual(st.party_markers[1].x, 30 + 24 * 10)

    def test_special_flag_disables_world_song_pause_and_fade(self):
        music_events = []
        manager = BattleController(
            on_music_fade=lambda *args: music_events.append("fade"),
            on_music_pause=lambda *args: music_events.append("pause"),
        )
        flags = [0] * 10
        flags[9] = 2
        manager.start_battle(1, 0, [], flags, party_members=self.party())
        manager.update(12)
        self.assertEqual(music_events, [])
        self.assertEqual(flags[9], 2)

    def test_fractional_updates_preserve_transitional_sound_timing(self):
        events = []
        manager = BattleController(on_sound=lambda name, vol, st: events.append(st.elapsed_frames))
        st = manager.start_battle(1, 0, [], {}, party_members=self.party())
        for _ in range(20):
            manager.update(0.5)
        self.assertEqual(st.elapsed_frames, 10)
        self.assertEqual(events, [10, 10])
        with self.assertRaises(ValueError):
            manager.update(-1)
        with self.assertRaises(ValueError):
            manager.update(float("nan"))

    def test_party_maximum_and_original_empty_slots(self):
        manager = BattleController()
        with self.assertRaises(ValueError):
            manager.start_battle(1, 0, [], {}, party_members=self.party() * 2)
        st = manager.start_battle(1, 0, [], {}, party_members=[])
        manager.update(24)
        self.assertTrue(st.intro_complete)  # No doom effects to wait for.


if __name__ == "__main__":
    unittest.main()
