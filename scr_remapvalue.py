"""Python port of ``gml_GlobalScript_scr_remapvalue``.

Contains the original three math helpers:

* ``scr_remapvalue(input_start, input_end, value, output_start, output_end)``
* ``remap(input_start, input_end, output_start, output_end, value)``
* ``remap_clamped(input_start, input_end, output_start, output_end, value)``

These functions are independent of game state and rendering.

``remap`` and ``remap_clamped`` use the separately ported
``scr_inverselerp`` helper, which returns 0 for a zero-width input interval.
The optional ``inverselerp=`` override is retained for compatibility with
existing callers.
"""

from collections.abc import Callable

from scr_inverselerp import scr_inverselerp


def _lerp(start: float, end: float, amount: float) -> float:
    """GML ``lerp(a, b, t)``: interpolation without implicit clamping."""
    return start + (end - start) * amount


def scr_remapvalue(
    input_start: float,
    input_end: float,
    value: float,
    output_start: float,
    output_end: float,
) -> float:
    """Map ``value`` from the input interval to the output interval.

    Unlike ``remap``, ``value`` is the THIRD positional argument.
    The source GML returns ``output_start`` if the input endpoints coincide.
    """
    if input_end == input_start:
        return output_start

    amount = (value - input_start) / (input_end - input_start)
    return _lerp(output_start, output_end, amount)


def remap(
    input_start: float,
    input_end: float,
    output_start: float,
    output_end: float,
    value: float,
    *,
    inverselerp: Callable[[float, float, float], float] | None = None,
) -> float:
    """Remap without clamping, as in the GML ``remap`` helper.

    ``value`` is the FIFTH positional argument. By default, uses the
    exact port of GML's ``scr_inverselerp``. An optional override remains
    available for callers that previously supplied one.
    """
    inverse = inverselerp if inverselerp is not None else scr_inverselerp
    amount = inverse(input_start, input_end, value)
    return _lerp(output_start, output_end, amount)


def remap_clamped(
    input_start: float,
    input_end: float,
    output_start: float,
    output_end: float,
    value: float,
    *,
    inverselerp: Callable[[float, float, float], float] | None = None,
) -> float:
    """Remap then clamp to the OUTPUT interval, including reversed bounds."""
    mapped = remap(
        input_start,
        input_end,
        output_start,
        output_end,
        value,
        inverselerp=inverselerp,
    )
    return max(min(output_start, output_end), min(max(output_start, output_end), mapped))


__all__ = ["scr_remapvalue", "remap", "remap_clamped"]
