"""Python ports of DELTARUNE's gml_GlobalScript_scr_depth_ext.

These functions update the ``depth`` attribute of a GameMaker-like instance.
They calculate depth only: a Python/Tkinter renderer must sort or restack
sprites using the resulting values for the visual order to change.
"""


def scr_depth_ext(state, base_depth=100000, multiplier=10):
    """Set depth using the instance y position and full sprite height.

    GML: depth = arg0 - ((y * arg1) + (sprite_height * arg1));
    """
    state.depth = base_depth - (
        (state.y * multiplier) + (state.sprite_height * multiplier)
    )


def scr_depth_ext_alt(state, base_depth=100000, multiplier=10):
    """Set depth using the sprite height adjusted by its y-origin offset.

    GML: depth = arg0 - ((y * arg1) +
                          ((sprite_height - sprite_yoffset) * arg1));
    """
    state.depth = base_depth - (
        (state.y * multiplier)
        + ((state.sprite_height - state.sprite_yoffset) * multiplier)
    )


def scr_depth_relative(state, base_depth=100000, offset=0, multiplier=10):
    """Set depth using the sprite's bottom edge minus a relative offset.

    GML: var __yy = (y + sprite_height) - arg1;
         depth = arg0 - (__yy * arg2);
    """
    yy = (state.y + state.sprite_height) - offset
    state.depth = base_depth - (yy * multiplier)


__all__ = [
    "scr_depth_ext",
    "scr_depth_ext_alt",
    "scr_depth_relative",
]
