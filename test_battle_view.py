"""Simple headless render-smoke checks for the battle preview overlay."""
from types import SimpleNamespace
import unittest
from battle import BattleController, PartySpawn
from battle_view import BattleCanvasView
from encounter_setup import setup_encounter
from battle_combat import BattleCombatController


class CanvasStub:
    def __init__(self):
        self.actions = []
    def winfo_width(self):
        return 640
    def winfo_height(self):
        return 480
    def delete(self, tag):
        self.actions.append(('delete', tag))
    def create_rectangle(self, *args, **kwargs):
        self.actions.append(('rect', args, kwargs))
    def create_text(self, *args, **kwargs):
        self.actions.append(('text', args, kwargs))
    def create_line(self, *args, **kwargs):
        self.actions.append(('line', args, kwargs))
    def create_oval(self, *args, **kwargs):
        self.actions.append(('oval', args, kwargs))
    def tag_raise(self, tag):
        self.actions.append(('raise', tag))


class BattleViewTests(unittest.TestCase):
    def test_attackpress_overlay_draws_bolts_without_advancing_clock(self):
        canvas = CanvasStub()
        game = SimpleNamespace(canvas=canvas, scale=2,
                               ui_to_screen=lambda x, y: (x*2, y*2))
        view = BattleCanvasView(game)
        layout = setup_encounter(1)
        view.start(layout)
        battle = BattleController()
        state = battle.start_battle(1, 0, layout.enemy_slots, {},
                                    party_members=[PartySpawn(1, 0, 0, 80, 140)])
        battle.update(24)
        combat = BattleCombatController(layout, (1,), {})
        combat.state.charaction[0] = 1
        combat.attack_phase()
        self.assertEqual(combat.attack_press.boltx, 0)
        view.render(state, combat)
        self.assertTrue(any(a[0] == 'line' for a in canvas.actions))
        self.assertTrue(any(a[0] == 'oval' for a in canvas.actions))
        self.assertEqual(combat.attack_press.boltx, 0)
        combat.update(1)
        view.render(state, combat)
        self.assertEqual(combat.attack_press.boltx, 1)

    def test_spellphase_overlay_renders_first_caster(self):
        canvas = CanvasStub()
        game = SimpleNamespace(canvas=canvas, scale=2,
                               ui_to_screen=lambda x, y: (x*2, y*2))
        view = BattleCanvasView(game)
        layout = setup_encounter(1)
        view.start(layout)
        battle = BattleController()
        state = battle.start_battle(1, 0, layout.enemy_slots, {},
                                    party_members=[PartySpawn(1, 0, 0, 80, 140)])
        battle.update(24)
        combat = BattleCombatController(layout, (1,), {})
        combat.state.charaction[0] = 2
        combat.attack_phase()
        combat.update(5)
        view.render(state, combat)
        self.assertTrue(any(a[0] == 'text' and 'SPELL' in a[2].get('text', '')
                            for a in canvas.actions))

    def test_entry_and_handoff_draw_without_sprite_assets(self):
        canvas = CanvasStub()
        game = SimpleNamespace(canvas=canvas, scale=2,
                               ui_to_screen=lambda x, y: (x * 2, y * 2))
        view = BattleCanvasView(game)
        layout = setup_encounter(1)
        view.start(layout)
        battle = BattleController(on_afterimage=view.add_afterimage)
        state = battle.start_battle(1, 0, layout.enemy_slots, {},
                                    party_members=[PartySpawn(1, 0, 0, 80, 140)])
        view.render(state)
        self.assertTrue(any(a[0] == 'rect' for a in canvas.actions))
        self.assertTrue(any(a == ('raise', 'battle_preview')
                            for a in canvas.actions))
        battle.update(24)
        view.render(state)
        self.assertTrue(any(a[0] == 'text' and
                            '* Test enemies showed up.' in a[2].get('text', '')
                            for a in canvas.actions))
        view.hide()
        self.assertIsNone(view.layout)


if __name__ == '__main__':
    unittest.main()
