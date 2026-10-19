"""Python port of DELTARUNE's ``gml_GlobalScript_draw_text_shadow_width``.

Draw text twice using the active renderer: a black shadow offset by (+1, +1)
and the foreground at the original position and color. The supplied ``state``
should expose ``draw_get_color()``, ``draw_set_color(color)``, and
``draw_text_width(x, y, text, width)``.

Optionally, ``state.string_hash_to_newline(text)`` can provide the project's
existing text-conversion logic; otherwise ``#`` is treated as a line break.
For Tkinter, the draw_text_width adapter can wrap Canvas.create_text(...,
width=width, anchor="nw"), passing in the current drawing color.
"""


def string_hash_to_newline(text) -> str:
    """Interpret DELTARUNE's hash-delimited line breaks in display text."""
    return str(text).replace("#", "\n")


def draw_text_shadow_width(state, x, y, text, width) -> None:
    """Draw wrapped text with a one-pixel black shadow.

    The foreground's color is the color active when this function is called.
    Restoring the previous color in a ``finally`` also prevents a rendering
    exception from leaving the rest of the game text black.
    """
    original_color = state.draw_get_color()
    converter = getattr(state, "string_hash_to_newline", None)
    display_text = (
        converter(text)
        if callable(converter)
        else string_hash_to_newline(text)
    )
    black = getattr(state, "c_black", "black")

    try:
        state.draw_set_color(black)
        state.draw_text_width(x + 1, y + 1, display_text, width)
    finally:
        state.draw_set_color(original_color)

    state.draw_text_width(x, y, display_text, width)
