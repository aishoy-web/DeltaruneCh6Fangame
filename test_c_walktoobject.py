"""Regression tests for c_walktoobject.py; run with python -m unittest."""
import unittest
from types import SimpleNamespace
from c_walktoobject import (
    c_walktoobject,
    c_delaywalktoobject,
    c_walktoobject_wait,
    c_delaywalktoobject_wait,
    c_walkto_actor,
    c_walkto_object,
    c_walkto,
)


class CutsceneSpy:
    def __init__(self):
        self.calls = []
        self.cutscene_master = SimpleNamespace(actor_id=["kris", "susie"])

    def c_cmd(self, *args):
        self.calls.append(("c_cmd", *args))

    def c_cmd_x(self, *args):
        self.calls.append(("c_cmd_x", *args))

    def c_wait(self, *args):
        self.calls.append(("c_wait", *args))

    def c_walkdirect(self, *args):
        self.calls.append(("c_walkdirect", *args))

    def c_delayfacing(self, *args):
        self.calls.append(("c_delayfacing", *args))


class TestWalkToObject(unittest.TestCase):
    def setUp(self):
        self.state = CutsceneSpy()
        self.target = SimpleNamespace(x=100, y=200)

    def test_direct(self):
        c_walktoobject(self.state, self.target, 4, -5, 20)
        self.assertEqual(self.state.calls, [("c_cmd", "walkdirect", 104, 195, 20, 0)])

    def test_delayed(self):
        c_delaywalktoobject(self.state, 8, self.target, -10, 3, 12)
        self.assertEqual(self.state.calls, [("c_cmd_x", "delaycmd", 8, "walkdirect", 90, 203, 12, 0)])

    def test_direct_wait(self):
        c_walktoobject_wait(self.state, self.target, 0, 0, 20)
        self.assertEqual(self.state.calls, [
            ("c_cmd", "walkdirect", 100, 200, 20, 0),
            ("c_wait", 20),
        ])

    def test_delayed_wait(self):
        c_delaywalktoobject_wait(self.state, 8, self.target, -5, 1, 12)
        self.assertEqual(self.state.calls, [
            ("c_cmd_x", "delaycmd", 8, "walkdirect", 95, 201, 12, 0),
            ("c_wait", 20),
        ])

    def test_actor_slot_lookup_defaults(self):
        c_walkto_actor(self.state, 1, 5, -2, 15)
        self.assertEqual(self.state.calls, [
            ("c_cmd_x", "walkto", "susie", 5, -2, 15, True, True),
        ])

    def test_actor_fallback(self):
        c_walkto_actor(self.state, 5, 0, 0, 4, False)
        self.assertEqual(self.state.calls, [
            ("c_cmd_x", "walkto", 5, 0, 0, 4, False, False),
        ])

    def test_actor_negative_not_python_index(self):
        with self.assertRaises(IndexError):
            c_walkto_actor(self.state, -1, 0, 0, 1)

    def test_actor_master_as_resource(self):
        self.state.cutscene_master = None
        self.state.obj_cutscene_master = "obj_cutscene_master"
        self.state.resolve_instance = lambda handle: SimpleNamespace(actor_id=[self.target])
        c_walkto_actor(self.state, 0, 2, 3, 10)
        self.assertEqual(self.state.calls, [
            ("c_cmd_x", "walkto", self.target, 2, 3, 10, True, True),
        ])

    def test_object_defaults(self):
        c_walkto_object(self.state, self.target, frames=16)
        self.assertEqual(self.state.calls, [
            ("c_cmd_x", "walkto", self.target, 0, 0, 16, True, False),
        ])

    def test_object_full_positional(self):
        c_walkto_object(self.state, self.target, 9, -7, 12, False)
        self.assertEqual(self.state.calls, [
            ("c_cmd_x", "walkto", self.target, 9, -7, 12, False, False),
        ])

    def test_object_missing_frames(self):
        with self.assertRaises(TypeError):
            c_walkto_object(self.state, self.target)

    def test_walkto_default_facing(self):
        c_walkto(self.state, self.target, 10)
        self.assertEqual(self.state.calls, [("c_walkdirect", 100, 200, 10)])

    def test_walkto_with_facing(self):
        c_walkto(self.state, self.target, 10, "left")
        self.assertEqual(self.state.calls, [
            ("c_walkdirect", 100, 200, 10),
            ("c_delayfacing", 11, "left"),
        ])

    def test_capture_target_at_queue_time(self):
        c_walktoobject(self.state, self.target, 1, 1, 5)
        self.target.x = 900
        self.assertEqual(self.state.calls[0][2], 101)


if __name__ == "__main__":
    unittest.main()
