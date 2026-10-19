"""Python port of gml_GlobalScript_scr_calculate_move_distance.

Returns a movement duration in frames based on two positions and movement
speed. Like GML's round(), Python's built-in round() uses ties-to-even
(banker's rounding).
"""

from math import hypot


def scr_calculate_move_distance(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    speed: float = 6,
) -> int:
    """Calculate the rounded travel time, never less than one frame.

    Args:
        x1, y1: Starting position.
        x2, y2: Destination.
        speed: Distance traveled per frame (default: 6).

    Returns:
        The duration in game frames, always at least 1 for valid values.

    Note:
        As in the GML formula, this divides by ``speed``. A speed of zero
        raises ZeroDivisionError in Python; callers should use nonzero speed.
    """
    move_time = 1
    distance_time = round(hypot(x2 - x1, y2 - y1) / speed)

    if distance_time > move_time:
        move_time = distance_time

    return move_time
