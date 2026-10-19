"""Python port of ``gml_GlobalScript_scr_get_inputs``.

Populate the caller's directional and action input fields from the current
input frame.  This script does not perform keyboard or gamepad polling itself;
those are delegated to methods on ``state`` (e.g. ``left_h()`` and
``button2_p()``), just as the original GML delegates to input helpers.

Required when enabled:
    state.left_h/right_h/up_h/down_h()       held directions
    state.left_p/right_p/up_p/down_p()       just-pressed directions
    state.button1_h/button1_p()             primary input
    state.button2_h/button2_p()             secondary input
    state.button4_h/button4_p()             conditional extra input
    state.gp_face3                           GML gp_face3 input constant
    state.global_state.flag[25]             jump/attack swap setting
    state.global_state.input_g[6]           configured button 4 mapping

If the state itself stores the globals, ``global_state`` is optional.

Output attributes:
    key_left, key_right, key_up, key_down
    press_left, press_right, press_up, press_down
    vinput, hinput
    press_jump, key_jump, press_attack, key_attack

Following GML, a disabled call explicitly clears all these fields.  The
function returns None; its effects are made on the supplied state object.
"""


def scr_get_inputs(state, enabled):
    """Update the caller's directional/jump/attack fields for this frame."""
    if enabled:
        # Held directional input.
        state.key_left = bool(state.left_h())
        state.key_right = bool(state.right_h())
        state.key_up = bool(state.up_h())
        state.key_down = bool(state.down_h())

        # Newly pressed directional input (not the same as held input).
        state.press_left = bool(state.left_p())
        state.press_right = bool(state.right_p())
        state.press_up = bool(state.up_p())
        state.press_down = bool(state.down_p())

        # GameMaker subtracts booleans to obtain -1, 0, or 1.
        state.vinput = int(state.key_down) - int(state.key_up)
        state.hinput = int(state.key_right) - int(state.key_left)

        globals_ = getattr(state, "global_state", state)
        xfree = globals_.input_g[6] != state.gp_face3

        if globals_.flag[25] == 0:
            state.press_jump = bool(
                state.button2_p() or (xfree and state.button4_p())
            )
            state.key_jump = bool(
                state.button2_h() or (xfree and state.button4_h())
            )
            state.press_attack = bool(
                state.button1_p() or (not xfree and state.button4_p())
            )
            state.key_attack = bool(
                state.button1_h() or (not xfree and state.button4_h())
            )
        else:
            state.press_jump = bool(
                state.button1_p() or (not xfree and state.button4_p())
            )
            state.key_jump = bool(
                state.button1_h() or (not xfree and state.button4_h())
            )
            state.press_attack = bool(
                state.button2_p() or (xfree and state.button4_p())
            )
            state.key_attack = bool(
                state.button2_h() or (xfree and state.button4_h())
            )
    else:
        state.key_left = False
        state.key_right = False
        state.key_up = False
        state.key_down = False
        state.press_left = False
        state.press_right = False
        state.press_up = False
        state.press_down = False
        state.vinput = 0
        state.hinput = 0
        state.press_jump = False
        state.key_jump = False
        state.press_attack = False
        state.key_attack = False
