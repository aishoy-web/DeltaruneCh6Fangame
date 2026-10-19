"""Python port of ``gml_GlobalScript_draw_sprite_part_ext_rot``.

Draw a cropped and rotated sprite through a GameMaker-style drawing adapter.

``state`` must provide:
    sprite_get_xoffset(sprite)
    sprite_get_yoffset(sprite)
    draw_sprite_general(sprite, subimage, left, top, width, height,
                        x, y, xscale, yscale, rotation,
                        color1, color2, color3, color4, alpha)

Like the GML original, negative crop start coordinates are clamped to 0.
``crop_x2`` and ``crop_y2`` are passed through the source's exact formulas:
    source_width  = crop_x2 / xscale - crop_left
    source_height = crop_y2 / yscale - crop_top
They are NOT treated as ordinary source widths or heights.

GameMaker's point_direction / lengthdir conventions use 0 degrees to the
right, 90 degrees up, with screen Y increasing downward. No drawing occurs
inside this function except the final delegated draw_sprite_general call.
"""

import math


def draw_sprite_part_ext_rot(
    state,
    sprite,
    subimage,
    crop_left,
    crop_top,
    crop_x2,
    crop_y2,
    x,
    y,
    xscale,
    yscale,
    rotation,
    color,
    alpha,
) -> None:
    """Draw a scaled/rotated sprite part, matching the supplied GML script."""
    # Original: if (arg2 < 0) arg2 = 0; if (arg3 < 0) arg3 = 0;
    crop_left = max(0, crop_left)
    crop_top = max(0, crop_top)

    xoffset = state.sprite_get_xoffset(sprite) * xscale
    yoffset = state.sprite_get_yoffset(sprite) * yscale
    newx = crop_left * xscale
    newy = crop_top * yscale

    # GameMaker point_direction(xoffset, yoffset, newx, newy) and
    # point_distance(xoffset, yoffset, newx, newy).
    dx = newx - xoffset
    dy = newy - yoffset
    theta = math.degrees(math.atan2(-dy, dx)) % 360
    radius = math.hypot(dx, dy)
    theta += rotation

    # GameMaker lengthdir_x(radius, theta) / lengthdir_y(radius, theta).
    angle_rad = math.radians(theta)
    draw_x = x + radius * math.cos(angle_rad)
    draw_y = y - radius * math.sin(angle_rad)

    # Preserve the exact GML cropping formulas, even for unusual scales.
    source_width = (crop_x2 / xscale) - crop_left
    source_height = (crop_y2 / yscale) - crop_top

    state.draw_sprite_general(
        sprite,
        subimage,
        crop_left,
        crop_top,
        source_width,
        source_height,
        draw_x,
        draw_y,
        xscale,
        yscale,
        rotation,
        color,
        color,
        color,
        color,
        alpha,
    )


__all__ = ["draw_sprite_part_ext_rot"]
