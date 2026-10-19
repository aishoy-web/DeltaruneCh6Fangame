"""Python port of DELTARUNE's ``gml_GlobalScript_c_step_func``.

Both helpers enqueue a function reference for the cutscene command system.
They do not execute the function when called.

``state`` must provide ``c_cmd(command_name, arg0, arg1, arg2, arg3)``.
The command handler is responsible for interpreting ``stepfunc`` and
``drawfunc`` and invoking the supplied function at the appropriate time.
"""


def c_step_func(state, func) -> None:
    """Queue ``func`` using the GML ``stepfunc`` cutscene command."""
    state.c_cmd("stepfunc", func, 0, 0, 0)


def c_draw_func(state, func) -> None:
    """Queue ``func`` using the GML ``drawfunc`` cutscene command."""
    state.c_cmd("drawfunc", func, 0, 0, 0)
