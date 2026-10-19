"""Unit tests for scr_get_inputs.py (run: python -m unittest -v test_scr_get_inputs)."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from scr_get_inputs import scr_get_inputs


INPUT_NAMES = (
    "left_h", "right_h", "up_h", "down_h",
    "left_p", "right_p", "up_p", "down_p",
    "button1_p", "button1_h", "button2_p", "button2_h",
    "button4_p", "button4_h",
)
OUTPUT_NAMES = (
    "key_left", "key_right", "key_up", "key_down",
    "press_left", "press_right", "press_up", "press_down",
    "vinput", "hinput",
    "press_jump", "key_jump", "press_attack", "key_attack",
)


def make_state(*, swapped=0, xfree=True, inputs=None, nested=True):
    state = SimpleNamespace(gp_face3=99)
    globals_ = SimpleNamespace(
        flag=[0] * 26,
        input_g=[0] * 7,
    )
    globals_.flag[25] = swapped
    globals_.input_g[6] = 0 if xfree else 99
    if nested:
        state.global_state = globals_
    else:
        state.flag = globals_.flag
        state.input_g = globals_.input_g
    inputs = inputs or {}
    for name in INPUT_NAMES:
        setattr(state, name, Mock(return_value=inputs.get(name, False)))
    return state


class TestGetInputs(unittest.TestCase):
    def test_disabled_clears_all_outputs_without_polling(self):
        state = make_state(inputs={"button1_p": True})
        for name in OUTPUT_NAMES:
            setattr(state, name, "stale")
        self.assertIsNone(scr_get_inputs(state, False))
        for name in OUTPUT_NAMES:
            self.assertEqual(getattr(state, name), 0 if name in ("vinput", "hinput") else False)
        for name in INPUT_NAMES:
            getattr(state, name).assert_not_called()

    def test_enabled_neutral(self):
        state = make_state()
        self.assertIsNone(scr_get_inputs(state, True))
        for name in OUTPUT_NAMES:
            self.assertEqual(getattr(state, name), 0 if name in ("vinput", "hinput") else False)

    def test_direction_signs_and_press_vs_hold(self):
        state = make_state(inputs={
            "left_h": True, "up_h": True, "right_p": True, "down_p": True
        })
        scr_get_inputs(state, True)
        self.assertEqual((state.hinput, state.vinput), (-1, -1))
        self.assertEqual((state.press_right, state.press_down), (True, True))
        self.assertEqual((state.key_right, state.key_down), (False, False))

    def test_opposite_directions_cancel(self):
        state = make_state(inputs={
            "left_h": True, "right_h": True, "up_h": True, "down_h": True
        })
        scr_get_inputs(state, True)
        self.assertEqual((state.hinput, state.vinput), (0, 0))

    def test_default_jump_button2_attack_button1(self):
        state = make_state(inputs={"button2_p": True, "button1_h": True})
        scr_get_inputs(state, True)
        self.assertTrue(state.press_jump)
        self.assertFalse(state.key_jump)
        self.assertFalse(state.press_attack)
        self.assertTrue(state.key_attack)

    def test_swap_jump_button1_attack_button2(self):
        state = make_state(swapped=1, inputs={"button1_p": True, "button2_h": True})
        scr_get_inputs(state, True)
        self.assertTrue(state.press_jump)
        self.assertFalse(state.key_jump)
        self.assertFalse(state.press_attack)
        self.assertTrue(state.key_attack)

    def test_button4_default_free_acts_as_jump(self):
        state = make_state(xfree=True, inputs={"button4_p": True, "button4_h": True})
        scr_get_inputs(state, True)
        self.assertEqual((state.press_jump, state.key_jump), (True, True))
        self.assertEqual((state.press_attack, state.key_attack), (False, False))

    def test_button4_default_bound_acts_as_attack(self):
        state = make_state(xfree=False, inputs={"button4_p": True, "button4_h": True})
        scr_get_inputs(state, True)
        self.assertEqual((state.press_jump, state.key_jump), (False, False))
        self.assertEqual((state.press_attack, state.key_attack), (True, True))

    def test_button4_swapped_free_acts_as_attack(self):
        state = make_state(swapped=1, xfree=True, inputs={"button4_p": True, "button4_h": True})
        scr_get_inputs(state, True)
        self.assertEqual((state.press_jump, state.key_jump), (False, False))
        self.assertEqual((state.press_attack, state.key_attack), (True, True))

    def test_button4_swapped_bound_acts_as_jump(self):
        state = make_state(swapped=1, xfree=False, inputs={"button4_p": True, "button4_h": True})
        scr_get_inputs(state, True)
        self.assertEqual((state.press_jump, state.key_jump), (True, True))
        self.assertEqual((state.press_attack, state.key_attack), (False, False))

    def test_direct_global_state(self):
        state = make_state(nested=False, swapped=1, inputs={"button1_h": True})
        scr_get_inputs(state, True)
        self.assertTrue(state.key_jump)

    def test_clears_after_enabled_frame(self):
        state = make_state(inputs={"left_h": True, "button2_p": True})
        scr_get_inputs(state, True)
        self.assertEqual(state.hinput, -1)
        self.assertTrue(state.press_jump)
        scr_get_inputs(state, False)
        self.assertEqual(state.hinput, 0)
        self.assertFalse(state.press_jump)
        self.assertFalse(state.key_left)

    def test_short_circuit_skips_button4_when_button2_true(self):
        state = make_state(xfree=True, inputs={"button2_p": True, "button2_h": True})
        scr_get_inputs(state, True)
        state.button4_p.assert_not_called()
        state.button4_h.assert_not_called()


if __name__ == "__main__":
    unittest.main()
