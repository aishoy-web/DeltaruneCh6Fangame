"""Python port of ``gml_GlobalScript_centerx``.

``state`` is the object invoking the original GML function. The remaining
positional arguments emulate GML's ``argument_count`` and ``argument[]``.

The original script has some surprising behavior that is intentionally kept:
* With no arguments, ``sprite_width`` is not multiplied by ``image_xscale``.
* With one argument, the sprite and scale come from the argument, but ``x``
  comes from the caller, not the argument.
* With two arguments, the first is ignored and the caller's bbox is used
  only if the second argument is nonzero.
* Unassigned ``truexcenter`` is represented by Python ``None`` (GML undefined).
"""


def centerx(state, *args):
    """Return the GML-style horizontal center for the calling object.

    Requires ``state.sprite_get_xoffset(sprite)`` and, for the one-argument
    form, ``state.sprite_get_width(sprite)``. Other required attributes vary
    by the number of supplied arguments.
    """
    count = len(args)

    if count == 0:
        x1 = state.x - (
            state.sprite_get_xoffset(state.sprite_index) * state.image_xscale
        )
        x2 = x1 + state.sprite_width
        return (x1 + x2) / 2

    if count == 1:
        source = args[0]
        x1 = state.x - (
            state.sprite_get_xoffset(source.sprite_index) * source.image_xscale
        )
        x2 = x1 + (
            state.sprite_get_width(source.sprite_index) * source.image_xscale
        )
        return (x1 + x2) / 2

    if count == 2:
        if args[1] != 0:
            return (state.bbox_left + state.bbox_right) / 2
        return None

    return None
