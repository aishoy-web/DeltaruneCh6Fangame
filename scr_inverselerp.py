"""Python port of gml_GlobalScript_scr_inverselerp.

Both original GML entry points use the same formula and return 0 when the
input interval has zero width. Neither function clamps the result.
"""


def inverselerp(start: float, end: float, value: float) -> float:
    """Return the interpolation fraction for ``value`` within ``start``–``end``.

    Equal endpoints return 0, exactly as in the supplied GML.
    Values outside the input interval are allowed to produce values outside
    [0, 1].
    """
    if end == start:
        return 0
    return (value - start) / (end - start)


def scr_inverselerp(start: float, end: float, value: float) -> float:
    """Compatibility name matching the original ``scr_inverselerp`` script."""
    if end == start:
        return 0
    return (value - start) / (end - start)


__all__ = ["inverselerp", "scr_inverselerp"]
