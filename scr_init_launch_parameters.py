"""Python port of ``gml_GlobalScript_scr_init_launch_parameters``.

Exports the constructor ``launch_parameters`` and both accompanying GML
functions: ``scr_init_launch_parameters`` and
``get_chapter_switch_parameters``.

The parser accepts Python command-line arguments (``sys.argv[1:]``) by default.
For game-engine integration, pass ``state`` with ``parameter_count()`` and
``parameter_string(index)`` adapters, or pass ``parameters=[...]`` explicitly.

``get_chapter_switch_parameters(state)`` reads ``state.global_state`` (or
``state`` directly) and calls ``state.scr_is_switch_os()`` if available.
Callers can override that check using ``is_switch_os=True/False``.

Source GML quirks intentionally preserved:
* ``switch_`` is detected anywhere within a parameter, not just at its start.
* The numerical value comes from ``parameter.split('_')[1]``.
* ``returning_N`` is generated for chapter switches, but not parsed at launch.
* The emitted string begins with one space and always includes ``launcher``.
"""

from dataclasses import dataclass
import math
import sys
from typing import Iterable


@dataclass
class LaunchParameters:
    """Equivalent of GML's ``new launch_parameters()`` constructor."""

    is_launcher: bool = False
    switch_id: int | float = -1
    returning: int = 0


# Retain the original GML constructor's public name as well.
launch_parameters = LaunchParameters


def _parse_real(text: str) -> int | float:
    """Convert GML-style numeric strings to Python numbers.

    GameMaker's ``real()`` errors for invalid strings and supports hexadecimal
    notation. Preserve an integral result as an int for clearer rendering.
    """
    value = text.strip()
    if value.lower().startswith("0x"):
        return int(value, 16)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Invalid switch ID: {text!r}")
    return int(number) if number.is_integer() else number


def _collect_parameters(state, parameters: Iterable[str] | None) -> list[str]:
    if parameters is not None:
        return list(parameters)
    if state is None:
        # GameMaker parameter_string(0) is the executable name, which Python
        # exposes as sys.argv[0]; GML starts checking at 1.
        return sys.argv[1:]

    count_fn = getattr(state, "parameter_count", None)
    string_fn = getattr(state, "parameter_string", None)
    if callable(count_fn) and callable(string_fn):
        return [string_fn(i + 1) for i in range(int(count_fn()))]
    if callable(count_fn) or callable(string_fn):
        raise AttributeError(
            "state must provide both parameter_count() and parameter_string()"
        )
    # A state object without parameter adapters can still run in Python.
    return sys.argv[1:]


def scr_init_launch_parameters(
    state=None,
    *,
    parameters: Iterable[str] | None = None,
) -> LaunchParameters:
    """Parse launch flags into a new ``LaunchParameters`` instance.

    Accepts the exact GML forms ``launcher`` and ``switch_<number>``.
    The GML initializer does not read ``returning_<chapter>``.
    """
    param_data = launch_parameters()
    for param in _collect_parameters(state, parameters):
        if param == "launcher":
            param_data.is_launcher = True
        elif "switch_" in param:
            # This intentionally matches GML's string_pos(...) != 0 followed
            # by string_split(param, '_')[1], rather than using startswith.
            pieces = param.split("_")
            param_data.switch_id = _parse_real(pieces[1])
    return param_data


def _gml_string(value) -> str:
    """Render numeric values without a Python-only trailing '.0'."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def get_chapter_switch_parameters(
    state,
    *,
    is_switch_os: bool | None = None,
) -> str:
    """Build the GML-formatted chapter-switch parameter string.

    ``state`` is the game context; the global data lives in
    ``state.global_state`` when provided. A Switch OS check is performed
    through ``state.scr_is_switch_os()`` unless explicitly overridden.
    """
    global_state = getattr(state, "global_state", state)
    launch_data = launch_parameters()
    launch_data.is_launcher = global_state.launcher

    if is_switch_os is None:
        switch_check = getattr(state, "scr_is_switch_os", None)
        is_switch_os = bool(switch_check()) if callable(switch_check) else False

    if is_switch_os and hasattr(global_state, "switchlogin"):
        launch_data.switch_id = global_state.switchlogin

    parameters = [
        "launcher",
        "switch_" + _gml_string(launch_data.switch_id),
        "returning_" + _gml_string(global_state.chapter),
    ]
    return "".join(" " + param for param in parameters)


__all__ = [
    "LaunchParameters",
    "launch_parameters",
    "scr_init_launch_parameters",
    "get_chapter_switch_parameters",
]
