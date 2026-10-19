"""Python port of DELTARUNE's gml_GlobalScript_scr_spritematch.

Copy a source instance's sprite and visual-transform properties onto the
instance that invokes the script. The original GML does not copy animation
speed, origin, collision mask, depth, or other object state.
"""


def scr_spritematch(state, source):
    """Match *state*'s sprite, position, and image appearance to *source*.

    Args:
        state: Destination object (GML's implicit ``self``).
        source: Source object (GML's ``arg0``).

    Returns:
        None, just as a GML script with no explicit return.
    """
    state.sprite_index = source.sprite_index
    state.image_index = source.image_index
    state.x = source.x
    state.y = source.y
    state.image_blend = source.image_blend
    state.image_alpha = source.image_alpha
    state.image_angle = source.image_angle
    state.image_xscale = source.image_xscale
    state.image_yscale = source.image_yscale
