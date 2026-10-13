"""Test the Game.start_battle integration without loading Tk or missing sprites.

Extract only the integration methods from game.py's AST. The full game import
requires the fangame's resources and its other modules, unavailable in this
standalone source snapshot.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

from battle import BattleController, PartySpawn
from battle_view import BattleCanvasView
from encounter_setup import setup_encounter


def load_battle_methods():
    source = Path(__file__).with_name('game.py').read_text(encoding='utf8')
    game_cls = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.ClassDef) and n.name == 'Game')
    wanted = {'start_battle', '_battle_controller_handoff', 'end_battle_preview'}
    funcs = [n for n in game_cls.body
             if isinstance(n, ast.FunctionDef) and n.name in wanted]
    assert len(funcs) == len(wanted)
    klass = ast.ClassDef(name='GameBattleFragment', bases=[], keywords=[],
                         body=funcs, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[klass], type_ignores=[]))
    namespace = {'setup_encounter': setup_encounter, 'PartySpawn': PartySpawn}
    exec(compile(module, str(Path(__file__).with_name('game.py')), 'exec'), namespace)
    return namespace['GameBattleFragment']


class DummyController:
    def __init__(self):
        self.closed = 0
    def close(self):
        self.closed += 1


class DummyView:
    def __init__(self):
        self.layout = None
        self.frames = []
    def start(self, layout):
        self.layout = layout
    def render(self, state):
        self.frames.append(state.elapsed_frames)
    def hide(self):
        self.layout = None


class BattleGameIntegrationTests(unittest.TestCase):
    def setUp(self):
        fragment = load_battle_methods()
        class FakeGame(fragment):
            pass
        game = FakeGame()
        game.state = 'playing'
        game.battle_flags = {}
        game.battle_party_ids = (1,)
        game.camera_x = 100
        game.camera_y = 20
        game.player = SimpleNamespace(
            x=122, y=40,
            animation=SimpleNamespace(stop_at_next_rest_frame=lambda: None),
        )
        game.menu = DummyController()
        game.hud = DummyController()
        game.keys_pressed = {'Down'}
        game.direction_keys = ['Down']
        game.was_moving = True
        game.dialogue_writer = SimpleNamespace(active=False)
        game.dialogue_box = SimpleNamespace(hide=lambda: None)
        game.battle_view = DummyView()
        game.battle = BattleController(on_controller_start=game._battle_controller_handoff)
        game.audio = SimpleNamespace(unpause_music=lambda: None)
        game.render_dynamic = lambda: None
        self.game = game

    def test_starts_from_actual_player_position_and_freezes_input(self):
        g = self.game
        st = g.start_battle(203)
        self.assertEqual(g.state, 'battle_intro')
        self.assertEqual((st.party_markers[0].x, st.party_markers[0].y), (44, 40))
        self.assertEqual((st.party_markers[0].target_x, st.party_markers[0].target_y),
                         (80, 140))
        self.assertEqual([d.monster_type for d in g.battle_layout.enemy_definitions],
                         [73, 73])
        self.assertEqual(g.battle_flags[9], 1)
        self.assertEqual(g.direction_keys, [])
        self.assertFalse(g.keys_pressed)
        self.assertFalse(g.was_moving)
        self.assertEqual(g.battle_view.frames, [0])
        self.assertEqual(g.menu.closed, 1)
        with self.assertRaises(RuntimeError):
            g.start_battle(204)
        g.battle.update(23)
        self.assertEqual(g.state, 'battle_intro')
        g.battle.update(1)
        self.assertEqual(g.state, 'battle_ready')
        self.assertFalse(st.intro_complete)
        g.battle.update(1)
        self.assertTrue(st.intro_complete)

    def test_requires_follower_origins_until_follower_objects_exist(self):
        g = self.game
        with self.assertRaises(ValueError):
            g.start_battle(228, party_ids=(1, 2, 3))
        st = g.start_battle(
            228, party_ids=(1, 2, 3),
            follower_origins=((120, 50), (130, 60)),
        )
        self.assertEqual(len(st.party_markers), 3)
        self.assertEqual(st.party_markers[1].sprite, 'spr_susier_wall')
        self.assertEqual(st.party_markers[2].sprite, 'spr_ralsei_dark')
        self.assertEqual(st.party_markers[0].target_y, 50)
        self.assertEqual(st.party_markers[1].target_y, 122)
        self.assertEqual(st.party_markers[2].target_y, 200)

    def test_debug_exit_restores_overworld_and_original_battle_flag(self):
        g = self.game
        g.battle_flags[9] = 2
        g.start_battle(1)
        self.assertEqual(g.battle_flags[9], 2)
        g.end_battle_preview()
        self.assertEqual(g.battle_flags[9], 2)
        self.assertIsNone(g.battle.state)
        self.assertIsNone(g.battle_layout)
        self.assertIsNone(g.battle_view.layout)
        self.assertEqual(g.state, 'playing')

    def test_blocks_invalid_entry_and_oversized_party(self):
        g = self.game
        g.state = 'file_select'
        with self.assertRaises(RuntimeError):
            g.start_battle(1)
        g.state = 'playing'
        with self.assertRaises(ValueError):
            g.start_battle(1, party_ids=(2, 1))
        with self.assertRaises(ValueError):
            g.start_battle(1, party_ids=(1, 2, 3, 4))


if __name__ == '__main__':
    unittest.main()
