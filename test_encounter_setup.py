"""Tests against the supplied Chapter 5 scr_encountersetup GML."""
import random
import unittest

from encounter_setup import (
    CUSTOM_ENCOUNTERS, SOURCE_ENCOUNTERS, register_encounter, setup_encounter,
)


class EncounterSetupTests(unittest.TestCase):
    def tearDown(self):
        CUSTOM_ENCOUNTERS.clear()

    def test_all_recovered_cases_stay_accessible(self):
        self.assertEqual(len(SOURCE_ENCOUNTERS), 76)
        for number in SOURCE_ENCOUNTERS:
            with self.subTest(number=number):
                layout = setup_encounter(number, (1, 2, 3))
                self.assertEqual(len(layout.enemy_slots), 3)
                self.assertGreaterEqual(len(layout.enemy_definitions), 1)
                self.assertLessEqual(len(layout.enemy_definitions), 3)
                self.assertEqual(len(layout.hero_positions), 3)
                self.assertEqual(layout.number, number)

    def test_case_zero_uses_initial_gml_defaults_not_switch_default(self):
        layout = setup_encounter(0)
        self.assertEqual([(e.object_name, e.x, e.y)
                          for e in layout.enemy_definitions],
                         [('obj_baseenemy', 500, 40)])
        self.assertEqual(layout.battle_message, '* It is known.')

    def test_unknown_number_uses_switch_default_two_enemies(self):
        layout = setup_encounter(99999)
        self.assertEqual([(e.x, e.y) for e in layout.enemy_definitions],
                         [(480, 110), (500, 200)])
        self.assertIsNone(layout.enemy_slots[2])

    def test_source_case_one_two_enemies(self):
        l = setup_encounter(1)
        self.assertEqual([(e.monster_type, e.x, e.y)
                          for e in l.enemy_definitions], [(1, 480, 110), (1, 500, 200)])
        self.assertEqual(l.battle_message, '* Test enemies showed up.')

    def test_three_enemies_and_exact_ids(self):
        l = setup_encounter(210)
        self.assertEqual([(e.object_name, e.monster_type, e.x, e.y)
                          for e in l.enemy_definitions],
                         [('obj_scarecrow_enemy', 72, 473, 24),
                          ('obj_kawkaw_enemy', 74, 446, 153),
                          ('obj_kawkaw_enemy', 74, 483, 240)])

    def test_global_char_party_formations(self):
        self.assertEqual(setup_encounter(1, (1,)).hero_positions,
                         [(80, 140), (80, 130), (80, 210)])
        self.assertEqual(setup_encounter(1, (1, 2)).hero_positions,
                         [(80, 100), (80, 180), (80, 210)])
        self.assertEqual(setup_encounter(1, (1, 2, 3)).hero_positions,
                         [(80, 50), (80, 130), (80, 210)])

    def test_227_228_special_partyconfig_formations(self):
        for number in (227, 228):
            self.assertEqual(setup_encounter(number, (1,)).hero_positions,
                             [(80, 122), (80, 122), (72, 200)])
            self.assertEqual(setup_encounter(number, (1, 2)).hero_positions,
                             [(94, 86), (80, 166), (72, 200)])
            self.assertEqual(setup_encounter(number, (1, 2, 3)).hero_positions,
                             [(94, 50), (80, 122), (72, 200)])

    def test_special_hero_positions_for_226_230_and_25(self):
        self.assertEqual(setup_encounter(226).hero_positions[:2],
                         [(90, 32), (80, 104)])
        self.assertEqual(setup_encounter(230).hero_positions[:2],
                         [(90, 32), (90, 104)])
        self.assertEqual(setup_encounter(25).hero_positions,
                         [(80, 100), (90, 150), (100, 210)])

    def test_genuinely_empty_opening_text_is_not_replaced(self):
        self.assertEqual(setup_encounter(226).battle_message, '')
        self.assertEqual(setup_encounter(230).battle_message, '')
        self.assertEqual(setup_encounter(777).battle_message, ' ')

    def test_localized_message_flag_overrides(self):
        for number, name in [(4, 'Rudinn'), (21, 'Jigsawry')]:
            self.assertEqual(setup_encounter(number, flags={500: 0}).battle_message,
                             f'* {name} drew near!')
            self.assertEqual(setup_encounter(number, flags={500: 1}).battle_message,
                             f'* A different {name} from last time drew near!')
            self.assertEqual(setup_encounter(number, flags={500: 2}).battle_message,
                             f'* Assumedly another different {name} appeared!')
            self.assertEqual(setup_encounter(number, flags={500: -1}).battle_message,
                             f'* {name} drew near!')

    def test_random_side_effect_for_case_93(self):
        flags = {500: 7}
        rng = random.Random(1)
        setup_encounter(93, flags=flags, rng=rng)
        self.assertIn(flags[426], (0, 1, 2, 3))
        self.assertEqual(flags[500], 7)

    def test_case_three_uses_overworld_npc_coordinates(self):
        layout = setup_encounter(3, npc_origin=(1000, 1250),
                                 camera_origin=(200, 300))
        self.assertEqual((layout.enemy_definitions[0].x,
                          layout.enemy_definitions[0].y), (1000, 1250))

    def test_stage_camera_origin_offsets_all_positions(self):
        l = setup_encounter(204, party_ids=(1, 2), camera_origin=(180, 240))
        self.assertEqual(l.hero_positions[:2], [(260, 340), (260, 420)])
        self.assertEqual((l.enemy_definitions[0].x, l.enemy_definitions[0].y),
                         (660, 350))

    def test_enemy_sprite_registry_preserves_object_name(self):
        l = setup_encounter(203, enemy_sprites={'obj_shinobeetle_enemy': 'spr_shinobeetle'})
        self.assertEqual(l.enemy_slots[0].sprite, 'spr_shinobeetle')
        self.assertEqual(l.resource_names[:2], ['obj_shinobeetle_enemy', 'obj_shinobeetle_enemy'])

    def test_source_typo_is_not_silently_rewritten(self):
        self.assertIn('Floradinn', setup_encounter(209).battle_message)
        self.assertEqual(setup_encounter(209).enemy_definitions[1].object_name,
                         'obj_leafling_enemy')

    def test_chapter_six_registration_and_safety(self):
        register_encounter(1000, [('obj_ch6_test', 800, 450, 180)], '* A new foe!')
        l = setup_encounter(1000)
        self.assertEqual(l.battle_message, '* A new foe!')
        self.assertEqual(l.enemy_slots[0].monster_type, 800)
        self.assertEqual(l.resource_names[0], 'obj_ch6_test')
        with self.assertRaises(ValueError):
            register_encounter(1, [], 'duplicate')
        with self.assertRaises(ValueError):
            register_encounter('4', [], 'also duplicate')
        with self.assertRaises(ValueError):
            register_encounter(1001, [('e', 1, 0, 0)] * 4, 'too many')

    def test_rejects_four_party_slots(self):
        with self.assertRaises(ValueError):
            setup_encounter(1, (1, 2, 3, 4))


if __name__ == '__main__':
    unittest.main()
