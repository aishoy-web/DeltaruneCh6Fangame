"""Python ports of DELTARUNE's ``gml_GlobalScript_scr_bitmask``.

Bit fields are stored least-significant first. Values may use a configurable
number of bits per entry; the packing helper restricts the result to 18 bits,
matching the original GML implementation.

Functions that emit ``scr_debug_print`` messages accept an optional keyword-only
``debug_print`` callback. Without one, warnings are written using Python's
``logging`` module. No game-state object is necessary for these pure helpers.
"""

from math import floor
import logging


_LOGGER = logging.getLogger(__name__)


def _require_positive_bits(bits):
    """Reject bit widths Python cannot safely use as shift counts."""
    if not isinstance(bits, int) or isinstance(bits, bool) or bits <= 0:
        raise ValueError("bits_per_value must be a positive integer")


def _debug_print(message, callback):
    if callback is not None:
        callback(message)
    else:
        _LOGGER.warning("%s", message)


def scr_array_to_bitmask(values, bits_per_value=1, *, debug_print=None):
    """Pack a sequence of values into a bitmask, using at most 18 bits.

    Values are ordered from least to most significant. An overlong sequence is
    truncated. Invalid values are floored and clamped to the available range,
    matching the original GML function.
    """
    _require_positive_bits(bits_per_value)
    maxvalue = (1 << bits_per_value) - 1
    new_flag = 0
    array_length = len(values)
    max_entries = floor(18 / bits_per_value)

    if array_length > max_entries:
        _debug_print(
            f"Warning! values_to_bitmask: Array too long. "
            f"Truncating to {max_entries}",
            debug_print,
        )

    for i in range(min(array_length, max_entries)):
        value = values[i]
        if value > maxvalue or value < 0 or floor(value) != value:
            # The missing space after the index is present in the GML text.
            _debug_print(
                f"Warning! values_to_bitmask: Value {i}"
                "is too large, too small or not an integer.",
                debug_print,
            )
            value = max(0, min(floor(value), maxvalue))
            _debug_print(f"Fixed Value: {value}", debug_print)

        new_flag |= (int(value) & maxvalue) << (i * bits_per_value)

    return new_flag


def scr_bitmask_to_array(bitmask, count, bits_per_value=1):
    """Read ``count`` values from a bitmask, least-significant first."""
    _require_positive_bits(bits_per_value)
    maxvalue = (1 << bits_per_value) - 1
    return [
        (int(bitmask) >> (i * bits_per_value)) & maxvalue
        for i in range(count)
    ]


def scr_set_bitmask_value(
    bitmask, index, value, bits_per_value=1, *, debug_print=None
):
    """Replace one packed value and return the resulting integer bitmask.

    Mirrors GML's bounds *warning* (``index > 18 / bits_per_value``), but does
    not clamp the index or prevent writing outside the recommended 18-bit area.
    """
    _require_positive_bits(bits_per_value)
    maxvalue = (1 << bits_per_value) - 1

    if value > maxvalue or value < 0 or floor(value) != value:
        _debug_print(
            f"Warning! scr_set_bitmask_value: Value {value} "
            "is too large, too small or not an integer.",
            debug_print,
        )
        value = max(0, min(floor(value), maxvalue))
        _debug_print(f"Fixed Value: {value}", debug_print)

    if index > 18 / bits_per_value:
        _debug_print("ERROR: WRITING OUT OF BITMASK BOUNDS", debug_print)

    shift = index * bits_per_value
    bitmask = int(bitmask) & ~(maxvalue << shift)
    bitmask |= (int(value) & maxvalue) << shift
    return bitmask


def scr_get_bitmask_value(bitmask, index, bits_per_value=1):
    """Extract the value at ``index`` from a packed bitmask."""
    _require_positive_bits(bits_per_value)
    maxvalue = (1 << bits_per_value) - 1
    return (int(bitmask) >> (index * bits_per_value)) & maxvalue
