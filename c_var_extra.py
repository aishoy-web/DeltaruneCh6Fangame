"""Python port of ``gml_GlobalScript_c_var_extra``.

All eight helpers enqueue cutscene commands through ``state.c_cmd_x``;
they do not change the target variables themselves.

For variable-arity helpers, the original GML distinguishes these supported
argument counts (excluding the added Python ``state`` argument):

* no-instance forms: 3, 4, or 5 arguments;
* instance forms: 4, 5, or 6 arguments.

With the shortest form, the final command value is 0. With the longest
form, the final two arguments are string-concatenated without a separator.
Arguments beyond the supported upper count are silently ignored by GML
(i.e., no cutscene command is queued), which this port preserves.

A call with fewer arguments than its minimum is invalid in this Python port
and raises TypeError rather than forwarding undefined GML arguments.
"""


def c_var_add(state, variable, value):
    """Queue an additive variable change on the cutscene's default target."""
    state.c_cmd_x("varadd", 0, variable, value, 0, 0, 0)


def c_var_add_instance(state, instance, variable, value):
    """Queue an additive variable change on a specified instance."""
    state.c_cmd_x("varadd", instance, variable, value, 0, 0, 0)


def _gml_string(state, value):
    """Use the engine's GML-compatible string conversion when available."""
    converter = getattr(state, "string", None)
    if callable(converter):
        return converter(value)
    # Python's str covers the usual numeric and textual command modifiers.
    # Nontrivial GML types may need the engine's string() adapter.
    return str(value)


def _queue_interpolation(state, command, arguments, *, instance_form=False, from_value=False):
    """Translate the GML argument_count branches without interpolating now."""
    count = len(arguments)
    minimum = 4 if instance_form else 3
    maximum = 6 if instance_form else 5

    if count < minimum:
        raise TypeError(
            f"Expected at least {minimum} GML argument(s), got {count}"
        )
    if count > maximum:
        # The original GML has no else branch for this count.
        return

    if instance_form:
        instance, variable, first, duration = arguments[:4]
        modifiers = arguments[4:]
    else:
        instance = 0
        variable, first, duration = arguments[:3]
        modifiers = arguments[3:]

    if not modifiers:
        option = 0
    elif len(modifiers) == 1:
        option = modifiers[0]
    else:
        option = (
            _gml_string(state, modifiers[0])
            + _gml_string(state, modifiers[1])
        )

    if from_value:
        state.c_cmd_x(command, instance, variable, first, 0, duration, option)
    else:
        state.c_cmd_x(command, instance, variable, 0, first, duration, option)


def c_var_lerp_add(state, *args):
    """Queue a ``varadd`` interpolation for the default cutscene target."""
    _queue_interpolation(state, "varadd", args)


def c_var_lerp_add_instance(state, *args):
    """Queue a ``varadd`` interpolation for a specified instance."""
    _queue_interpolation(state, "varadd", args, instance_form=True)


def c_var_lerp_to(state, *args):
    """Queue a ``varto`` interpolation from 0 to a supplied value."""
    _queue_interpolation(state, "varto", args)


def c_var_lerp_to_instance(state, *args):
    """Queue a ``varto`` interpolation on a specified instance."""
    _queue_interpolation(state, "varto", args, instance_form=True)


def c_var_lerp_from(state, *args):
    """Queue a ``varto`` interpolation from a supplied value to 0."""
    _queue_interpolation(state, "varto", args, from_value=True)


def c_var_lerp_from_instance(state, *args):
    """Queue a ``varto`` interpolation from a value to 0, on an instance."""
    _queue_interpolation(state, "varto", args, instance_form=True, from_value=True)
