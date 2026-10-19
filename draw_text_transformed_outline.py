"""Python port of gml_GlobalScript_draw_text_transformed_outline.

Draws an eight-pass outline around scaled text, then draws the text again
at its original coordinates using the color that was active on entry.

The ``state`` parameter is the Python equivalent of the calling GML instance.
It must expose three renderer methods:

    draw_get_color() -> color
    draw_set_color(color) -> None
    draw_text_transformed(x, y, text, xscale, yscale, angle) -> None

This helper only forwards drawing commands; it does not render text itself.
"""


def draw_text_transformed_outline(
    state,
    x,
    y,
    text,
    xscale,
    yscale,
    outline_color=0,
) -> None:
    """Draw transformed text with an eight-position, scale-sized outline.

    Matches the original GML drawing order and its use of scale values both
    as text scales and as outline offsets. Rotation is always 0 degrees.

    ``outline_color=0`` preserves the original GML default (black).
    """
    old_color = state.draw_get_color()

    try:
        state.draw_set_color(outline_color)

        # Exact GML outline order; offsets are xscale and yscale, not 1 pixel.
        offsets = (
            (-xscale, 0),
            (-xscale, -yscale),
            (-xscale, +yscale),
            (+xscale, 0),
            (+xscale, +yscale),
            (+xscale, -yscale),
            (0, +yscale),
            (0, -yscale),
        )
        for dx, dy in offsets:
            state.draw_text_transformed(
                x + dx, y + dy, text, xscale, yscale, 0
            )
    finally:
        # Restore renderer state even if one of the outline passes fails.
        state.draw_set_color(old_color)

    state.draw_text_transformed(x, y, text, xscale, yscale, 0)
